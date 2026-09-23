/* Botão "Copiar token" da página do coletor.
 * O token é lido de um data-attribute (já escapado no HTML). A aplicação do
 * cookie no host do PORTAL é MANUAL, feita pelo apresentador no DevTools —
 * este botão só copia o valor para a área de transferência. */
(function () {
  "use strict";
  function copiar(texto) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(texto);
    }
    // Alternativa simples se a Clipboard API não estiver disponível.
    var ta = document.createElement("textarea");
    ta.value = texto;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e) {}
    document.body.removeChild(ta);
    return Promise.resolve();
  }

  var aviso = document.getElementById("copiado");
  document.querySelectorAll(".botao-copiar").forEach(function (b) {
    b.addEventListener("click", function () {
      copiar(b.getAttribute("data-token") || "").then(function () {
        if (!aviso) return;
        aviso.hidden = false;
        setTimeout(function () { aviso.hidden = true; }, 1500);
      });
    });
  });
})();
