const formsRequestingAction = document.querySelectorAll(".confirm-action")
formsRequestingAction?.forEach(form=>{
    const message = form.dataset.message
    form.addEventListener("submit",(event)=>{
        const response = confirm(message)
        if (!response){
            event.preventDefault()
        }
    })
})