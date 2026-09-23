/* Mural do Campus — script legítimo do portal.
 *
 * Fica em arquivo próprio (não inline) de propósito: assim, no modo corrigido,
 * a CSP "script-src 'self'" permite ESTE script e, ao mesmo tempo, bloqueia
 * qualquer <script> inline injetado num comentário.
 *
 * Única função: exibir UMA vez, por carregamento de página, o aviso de
 * segurança repetitivo do modo vulnerável (para observarmos a fadiga de
 * alerta). Sem loops, sem dezenas de alertas nativos. O botão "Entendi"
 * apenas fecha o modal. A fadiga de alerta NÃO é necessária para o XSS
 * executar — ela é só um comportamento de UX que o professor pediu para
 * demonstrar. A causa técnica do XSS é interpretar o comentário como código.
 */
(function () {
  "use strict";

  function iniciar() {
    var body = document.body;
    var modal = document.getElementById("modal-aviso");
    var ok = document.getElementById("modal-ok");
    if (!modal || !ok) return;

    // Só mostra quando o servidor marcou data-aviso="1" (modo vulnerável,
    // nas páginas de mural e de publicação).
    if (body.getAttribute("data-aviso") === "1") {
      modal.hidden = false;
      ok.focus();
      ok.addEventListener("click", function () {
        modal.hidden = true;
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
