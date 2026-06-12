(() => {
  const CONTACT_ENDPOINT = "/contact/submit";

  function fieldValue(form, name) {
    return String(new FormData(form).get(name) || "").trim();
  }

  function payloadFromForm(form) {
    const data = new FormData(form);
    return {
      contact_type: form.dataset.contactType || "Contato",
      name: fieldValue(form, "nome"),
      email: fieldValue(form, "email"),
      company: fieldValue(form, "empresa"),
      phone: fieldValue(form, "telefone"),
      subject: fieldValue(form, "assunto"),
      message: fieldValue(form, "mensagem") || "Solicitação de contato comercial.",
      consent: data.get("consentimento") === "on",
      website: fieldValue(form, "website"),
    };
  }

  function responseMessage(data, fallback) {
    if (typeof data?.detail === "string") {
      return data.detail;
    }
    if (typeof data?.message === "string") {
      return data.message;
    }
    return fallback;
  }

  document.querySelectorAll("[data-contact-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) {
        return;
      }

      const feedback = form.querySelector("[data-form-feedback]");
      const submitButton = form.querySelector('button[type="submit"]');
      const originalLabel = submitButton?.textContent || "Enviar";

      if (feedback) {
        feedback.className = "form-feedback";
        feedback.textContent = "Enviando solicitação...";
      }
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Enviando...";
      }

      try {
        const response = await fetch(CONTACT_ENDPOINT, {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify(payloadFromForm(form)),
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
          throw new Error(responseMessage(data, "Não foi possível enviar a solicitação."));
        }
        form.reset();
        if (feedback) {
          feedback.className = "form-feedback form-feedback-success";
          feedback.textContent = responseMessage(data, "Solicitação enviada. Nossa equipe entrará em contato.");
        }
      } catch (error) {
        if (feedback) {
          feedback.className = "form-feedback form-feedback-error";
          feedback.textContent = error instanceof Error
            ? error.message
            : "Não foi possível enviar a solicitação. Tente novamente ou use o WhatsApp.";
        }
      } finally {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.textContent = originalLabel;
        }
      }
    });
  });
})();
