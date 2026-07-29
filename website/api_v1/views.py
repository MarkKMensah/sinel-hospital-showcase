from rest_framework import generics
from rest_framework.response import Response
from accounts.api_v1.permissions import IsContentManager
from rest_api_v1.utils import ResponseMessage
from website.forms import AboutForm, ClientForm, ContactForm, MediaForm, OpeningHourForm, ServiceForm, SocialMediaLinkForm, TeamLeadForm
from website.models import About, Client, Contact, Media, OpeningHour, Service, SocialMediaLink, TeamLead
from .serializers import AboutSerializer, ClientSerializer, ContactSerializer, MediaSerializer, OpeningHourSerializer, ServiceSerializer, SocialMediaLinkSerializer, TeamLeadSerializer
from django.utils.html import strip_tags


class ContactApi(generics.GenericAPIView):
    """
    Returns the contact details.
    """
    permission_classes = [IsContentManager]
    serializer_class = ContactSerializer
    form_class = ContactForm

    def get(self, request, **kwargs):
        contact = Contact.objects.first()
        data = self.serializer_class(contact).data
        return Response({"contact": data})

    def put(self, request, **kwargs):
        contact = Contact.objects.first()
        form = self.form_class(request.data, instance=contact)
        if form.is_valid():
            form.save()
            data = self.serializer_class(contact).data
            return Response({"contact": data})
        else:
            # Return the first error.
            message = []
            for field, er in form.errors.items():
                message.append(f"{field}: [{strip_tags(er)}]")
            response = ResponseMessage(ResponseMessage.ERROR, str(message))
            return Response({"response": response.to_json()}, status=400)


class AboutAPI(generics.GenericAPIView):
    """
    Returns the about details.
    """
    permission_classes = [IsContentManager]
    serializer_class = AboutSerializer
    form_class = AboutForm

    def get(self, request, **kwargs):
        contact = About.objects.first()
        data = self.serializer_class(contact).data
        return Response({"about": data})

    def put(self, request, **kwargs):
        contact = About.objects.first()
        form = self.form_class(request.data, instance=contact)
        if form.is_valid():
            contact = form.save()
            data = self.serializer_class(contact).data
            return Response({"about": data})
        else:
            # Return the first error.
            message = []
            for field, er in form.errors.items():
                message.append(f"{field}: [{strip_tags(er)}]")
            response = ResponseMessage(ResponseMessage.ERROR, str(message))
            return Response({"response": response.to_json()}, status=400)


class CreateUpdateDeleteModelMixin(generics.GenericAPIView):
    permission_classes = [IsContentManager]

    def get(self, request, **kwargs):
        gallery = self.model_class.objects.all().order_by("-created_at")
        data = self.serializer_class(gallery,
                                     context={
                                         "request": request
                                     },
                                     many=True).data
        return Response({self.response_keyword_plural: data})

    def post(self, request, **kwargs):
        form = self.form_class(request.data, request.FILES)
        if form.is_valid():
            item = form.save()
            data = self.serializer_class(item, context={
                "request": request
            }).data
            return Response({self.response_keyword: data})
        else:
            # Return the first error.
            for field, er in form.errors.items():
                message = f"{field}: [{strip_tags(er)}]"
                response = ResponseMessage(ResponseMessage.ERROR, message)
                return Response({"response": response.to_json()})

    def patch(self, request, **kwargs):
        id = request.data.get("id")
        item = generics.get_object_or_404(self.model_class, id=id)
        form = self.form_class(request.data, request.FILES, instance=item)
        if form.is_valid():
            item = form.save()
            data = self.serializer_class(item, context={
                "request": request
            }).data
            return Response({self.response_keyword: data})
        else:
            # Return the first error.
            for field, er in form.errors.items():
                message = f"{field}: [{strip_tags(er)}]"
                response = ResponseMessage(ResponseMessage.ERROR, message)
                return Response({"response": response.to_json()})

    def delete(self, request, **kwargs):
        id = request.data.get("id")
        items = self.model_class.objects.filter(id=id)
        data = self.serializer_class(items.first(),
                                     context={
                                         "request": request
                                     }).data
        items.delete()
        return Response({self.response_keyword: data})


class MediaAPI(CreateUpdateDeleteModelMixin):
    """
    Returns the contact details.
    """
    permission_classes = [IsContentManager]
    serializer_class = MediaSerializer
    form_class = MediaForm
    serializer_class = MediaSerializer
    form_class = MediaForm
    model_class = Media
    response_keyword = "item"
    response_keyword_plural = "gallery"


class ServicesAPI(CreateUpdateDeleteModelMixin):
    """
    Returns the contact details.
    """
    permission_classes = [IsContentManager]
    serializer_class = ServiceSerializer
    form_class = ServiceForm
    model_class = Service
    response_keyword = "service"
    response_keyword_plural = "services"


class TeamLeadsAPI(CreateUpdateDeleteModelMixin):
    """
    Returns the list of team leads.
    """
    permission_classes = [IsContentManager]
    serializer_class = TeamLeadSerializer
    form_class = TeamLeadForm
    model_class = TeamLead
    response_keyword = "team_lead"
    response_keyword_plural = "team_leads"


class ClientsAPI(CreateUpdateDeleteModelMixin):
    """
    Returns the list of team clients and their stories.
    """
    permission_classes = [IsContentManager]
    serializer_class = ClientSerializer
    form_class = ClientForm
    model_class = Client
    response_keyword = "client"
    response_keyword_plural = "clients"


class OpeningHoursAPI(CreateUpdateDeleteModelMixin):
    """
    Returns a list opening and closing hours.
    """
    permission_classes = [IsContentManager]
    serializer_class = OpeningHourSerializer
    form_class = OpeningHourForm
    model_class = OpeningHour
    response_keyword = "opening_hour"
    response_keyword_plural = "opening_hours"


class SocialMediaLinksAPI(CreateUpdateDeleteModelMixin):
    """
    Returns the list of social media links.
    """
    permission_classes = [IsContentManager]
    serializer_class = SocialMediaLinkSerializer
    form_class = SocialMediaLinkForm
    model_class = SocialMediaLink
    response_keyword = "social_media_link"
    response_keyword_plural = "social_media_links"
