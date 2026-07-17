// MapToolsData.js

.pragma library

var tools = [
    {
        id: "pan",
        icon: "🖱️",
        shortcut: "V",
        group: 1,
        translationKey: "pan",
        names: { pt: "Mover", en: "Pan", es: "Mover", fr: "Déplacer" },
        desc: { pt: "Mover o mapa.", en: "Move the map.", es: "Mover el mapa.", fr: "Déplacer la carte." },
        isImplemented: true,
        hasProperties: false,
        settingsComponent: ""
    },
    {
        id: "brush",
        icon: "🖌️",
        shortcut: "B",
        group: 2,
        translationKey: "brush",
        names: { pt: "Pincel", en: "Brush", es: "Pincel", fr: "Pinceau" },
        desc: { pt: "Desenha livremente.", en: "Draw freely.", es: "Dibuja libremente.", fr: "Dessiner librement." },
        isImplemented: true,
        hasProperties: true,
        settingsComponent: "BrushSettings.qml",
        supportsOpacity: true,
        supportsThickness: true,
        supportsColor: true
    },
    {
        id: "arrow",
        icon: "↗️",
        shortcut: "L",
        group: 2,
        translationKey: "arrow",
        names: { pt: "Seta", en: "Arrow", es: "Flecha", fr: "Flèche" },
        desc: { pt: "Desenha uma linha ou seta.", en: "Draws a line or arrow.", es: "Dibuja una línea o flecha.", fr: "Dessine une ligne ou une flèche." },
        isImplemented: true,
        hasProperties: true,
        settingsComponent: "MapToolSettings.qml",
        supportsOpacity: true,
        supportsThickness: true,
        supportsColor: true
    },
    {
        id: "route",
        icon: "🛣️",
        shortcut: "R",
        group: 2,
        translationKey: "route",
        names: { pt: "Rota", en: "Route", es: "Ruta", fr: "Itinéraire" },
        desc: { pt: "Desenha uma rota segmentada.", en: "Draws a segmented route.", es: "Dibuja una ruta segmentada.", fr: "Dessine un itinéraire segmenté." },
        isImplemented: true,
        hasProperties: true,
        settingsComponent: "RouteSettings.qml",
        supportsOpacity: true,
        supportsThickness: true,
        supportsColor: true
    },
    {
        id: "polygon",
        icon: "⬟",
        shortcut: "P",
        group: 2,
        translationKey: "polygon",
        names: { pt: "Polígono", en: "Polygon", es: "Polígono", fr: "Polygone" },
        desc: { pt: "Desenha uma área fechada.", en: "Draws a closed area.", es: "Dibuja un área cerrada.", fr: "Dessine une zone fermée." },
        isImplemented: true,
        hasProperties: true,
        settingsComponent: "PolygonSettings.qml",
        supportsOpacity: true,
        supportsThickness: true,
        supportsColor: true,
        supportsFill: true
    },
    {
        id: "text",
        icon: "T",
        shortcut: "T",
        group: 3,
        translationKey: "text",
        names: { pt: "Texto", en: "Text", es: "Texto", fr: "Texte" },
        desc: { pt: "Adiciona um texto no mapa.", en: "Adds a text on the map.", es: "Añade un texto en el mapa.", fr: "Ajoute un texte sur la carte." },
        isImplemented: true,
        hasProperties: true,
        settingsComponent: "MapToolSettings.qml",
        supportsOpacity: true,
        supportsColor: true,
        supportsTextSize: true
    },
    {
        id: "logistics",
        icon: "🚚",
        shortcut: "O",
        group: 4,
        translationKey: "logistics",
        names: { pt: "Logística", en: "Logistics", es: "Logística", fr: "Logistique" },
        desc: { pt: "Calculadora de logística.", en: "Logistics calculator.", es: "Calculadora de logística.", fr: "Calculatrice de logistique." },
        isImplemented: true,
        hasProperties: false, // Uses its own LogisticsModal
        settingsComponent: ""
    },
    {
        id: "vehicle",
        icon: "📍",
        shortcut: "M",
        group: 4,
        translationKey: "vehicle",
        names: { pt: "Marcador / Veículo", en: "Marker / Vehicle", es: "Marcador / Vehículo", fr: "Marqueur / Véhicule" },
        desc: { pt: "Posiciona um ícone no mapa.", en: "Places an icon on the map.", es: "Coloca un icono en el mapa.", fr: "Place une icône sur la carte." },
        isImplemented: true,
        hasProperties: true,
        settingsComponent: "VehicleSettings.qml",
        supportsOpacity: true
    },
    {
        id: "artillery",
        icon: "🎯",
        shortcut: "A",
        group: 5,
        translationKey: "artillery",
        names: { pt: "Artilharia", en: "Artillery", es: "Artillería", fr: "Artillerie" },
        desc: { pt: "Calculadora de artilharia.", en: "Artillery calculator.", es: "Calculadora de artillería.", fr: "Calculatrice d'artillerie." },
        isImplemented: true,
        hasProperties: false, // Uses ArtilleryModal
        settingsComponent: ""
    },
    {
        id: "eraser",
        icon: "🗑️",
        shortcut: "E",
        group: 6,
        translationKey: "eraser",
        names: { pt: "Borracha", en: "Eraser", es: "Borrador", fr: "Gomme" },
        desc: { pt: "Apaga desenhos.", en: "Erases drawings.", es: "Borra dibujos.", fr: "Efface les dessins." },
        isImplemented: true,
        hasProperties: true,
        settingsComponent: "EraserSettings.qml"
    }
];

function getToolById(id) {
    for (var i = 0; i < tools.length; i++) {
        if (tools[i].id === id) return tools[i];
    }
    return null;
}

function cloneDrawing(drawing) {
    if (!drawing) return null;
    return JSON.parse(JSON.stringify(drawing));
}
