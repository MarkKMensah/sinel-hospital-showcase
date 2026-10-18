"""Signed, field-scoped dashboard revisions; no content is stored in the token."""

from contextlib import contextmanager
from hashlib import sha256
import json

from django.contrib.contenttypes.models import ContentType
from django.core import signing
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404


TOKEN_FIELD = "editor_revision"
CONFLICT_MESSAGE = (
    "This form is out of date or could not be verified. Your changes have not been "
    "saved. Open the latest version in another tab and compare before trying again."
)


def editor_instance(model, object_id):
    if not object_id:
        return None
    try:
        object_id = int(object_id)
    except (TypeError, ValueError):
        raise Http404("Content not found.")
    if not 1 <= object_id <= 9223372036854775807:
        raise Http404("Content not found.")
    return get_object_or_404(model, pk=object_id)


def fingerprint(model, instance, fields):
    values = {}
    if instance is not None and instance.pk:
        for name in sorted(fields):
            field = model._meta.get_field(name)
            value = field.value_from_object(instance)
            if field.many_to_many:
                value = sorted(item.pk for item in value)
            values[name] = value
    payload = {
        "model": model._meta.label_lower,
        "pk": instance.pk if instance is not None else None,
        "fields": sorted(fields),
        "values": values,
    }
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return sha256(serialized.encode("utf-8")).hexdigest()


def revision_token(model, instance, fields):
    return signing.dumps(fingerprint(model, instance, fields), salt="dashboard.editor")


def revision_matches(token, model, instance, fields):
    try:
        expected = signing.loads(token, salt="dashboard.editor")
    except (signing.BadSignature, TypeError, ValueError):
        return False
    return expected == fingerprint(model, instance, fields)


@contextmanager
def locked_editor_instance(model, object_id=None, *, singleton=False):
    """Use one ordering for singleton writes, including an empty installation.

    The content-type row exists after migrations, so it also serializes the first
    creation when there is not yet a content row to lock. Ordinary row updates
    only lock that resource. Backends without row locks retain their native
    transaction semantics; real-engine race evidence remains a separate gate.
    """
    with transaction.atomic():
        if singleton:
            content_type = ContentType.objects.get_for_model(model)
            ContentType.objects.select_for_update().get(pk=content_type.pk)
            instance = model.objects.select_for_update().first()
        elif object_id:
            instance = editor_instance(model, object_id)
            instance = model.objects.select_for_update().get(pk=instance.pk)
        else:
            instance = None
        yield instance
