document.addEventListener("DOMContentLoaded", () => {
  // =========================
  // INITIALIZE LUCIDE ICONS
  // =========================
  if (window.lucide) {
    lucide.createIcons();
  }

  // =========================
  // SMOOTH SCROLL FOR ANCHOR LINKS
  // =========================
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", function (e) {
      const href = this.getAttribute("href");

      // Ignore empty hash
      if (!href || href === "#") return;

      const target = document.querySelector(href);

      if (target) {
        e.preventDefault();
        target.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      }
    });
  });

  // =========================
  // CONTACT FORM SUBMIT
  // =========================
  const contactForm = document.getElementById("contactForm");
  const contactResult = document.getElementById("contactResult");

  if (contactForm) {
    const submitButton = contactForm.querySelector('button[type="submit"]');
    const originalButtonText = submitButton ? submitButton.innerHTML : "SEND MESSAGE";

    contactForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      const formData = new FormData(contactForm);

      // Disable button while sending
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.innerHTML = "SENDING...";
        submitButton.style.opacity = "0.7";
        submitButton.style.cursor = "not-allowed";
      }

      // Show loading message
      if (contactResult) {
        contactResult.innerHTML = `
          <p style="margin-top:14px; color:#1557ff; font-weight:600;">
            Sending message...
          </p>
        `;
      }

      try {
        const response = await fetch("/contact", {
          method: "POST",
          body: formData
        });

        let data;

        // Try parsing JSON safely
        try {
          data = await response.json();
        } catch (jsonError) {
          data = {
            success: false,
            message: "Invalid server response."
          };
        }

        if (response.ok && data.success) {
          if (contactResult) {
            contactResult.innerHTML = `
              <p style="margin-top:14px; color:green; font-weight:600;">
                ${data.message || "Your message has been sent successfully!"}
              </p>
            `;
          }

          contactForm.reset();
        } else {
          if (contactResult) {
            contactResult.innerHTML = `
              <p style="margin-top:14px; color:red; font-weight:600;">
                ${data.message || "Something went wrong. Please try again."}
              </p>
            `;
          }
        }
      } catch (error) {
        console.error("Contact form error:", error);

        if (contactResult) {
          contactResult.innerHTML = `
            <p style="margin-top:14px; color:red; font-weight:600;">
              Server error. Please try again later.
            </p>
          `;
        }
      } finally {
        // Re-enable button
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.innerHTML = originalButtonText;
          submitButton.style.opacity = "1";
          submitButton.style.cursor = "pointer";
        }
      }
    });
  }
});
