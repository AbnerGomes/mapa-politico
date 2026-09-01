(function () {
  "use strict";

  const form = document.getElementById("form-inicio");
  const erro = document.getElementById("form-erro");
  if (!form) return;

  const EMAIL_REGEX = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

  form.addEventListener("submit", (ev) => {
    ev.preventDefault();
    const nome = document.getElementById("input-nome").value.trim();
    const email = document.getElementById("input-email").value.trim();

    if (!nome) {
      mostrarErro("Digite seu nome pra continuar.");
      return;
    }
    if (!EMAIL_REGEX.test(email)) {
      mostrarErro("Digite um e-mail válido — é pra onde vamos mandar o PDF do resultado.");
      return;
    }

    sessionStorage.setItem("mp_nome", nome);
    sessionStorage.setItem("mp_email", email);
    window.location.href = "/quiz";
  });

  function mostrarErro(msg) {
    erro.textContent = msg;
    erro.hidden = false;
  }
})();
