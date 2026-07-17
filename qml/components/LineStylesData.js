.pragma library

var lineStyles = [
    { val: "solid", label: "Sólida", preview: "━━━━━━━━" },
    { val: "dashed", label: "Tracejada", preview: "━━  ━━  ━━" },
    { val: "dotted", label: "Pontilhada", preview: "- - - - - -" },
    { val: "advance", label: "Avanço", preview: "━━━━━━━►" },
    { val: "retreat", label: "Retirada", preview: "◄━━━━━━━" },
    { val: "double_movement", label: "Mov. Duplo", preview: "◄━━━━━━►" },
    { val: "defensive_line", label: "Linha Defensiva", preview: "━━▲━━▲━━" },
    { val: "barricade", label: "Barricada", preview: "▲▲▲▲▲▲▲▲" },
    { val: "barrier", label: "Barreira", preview: "││││││││" },
    { val: "minefield", label: "Campo Minado", preview: "━━✖━━✖━━" },
    { val: "checkpoint", label: "Checkpoint", preview: "━━■━━■━━" }
];

function getStyles() {
    return lineStyles;
}
