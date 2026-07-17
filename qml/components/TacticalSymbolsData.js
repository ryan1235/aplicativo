.pragma library

var symbols = [
    // DEFESA
    { id: "defense", icon: "🛡", fallbackIcon: "D", label: "Defesa", category: "Defesa" },
    { id: "bunker", icon: "🧱", fallbackIcon: "B", label: "Bunker", category: "Defesa" },
    { id: "barricade", icon: "🚧", fallbackIcon: "X", label: "Barricada", category: "Defesa" },
    // ATAQUE
    { id: "attack", icon: "⚔", fallbackIcon: "A", label: "Ataque", category: "Ataque" },
    { id: "artillery", icon: "🎯", fallbackIcon: "T", label: "Artilharia", category: "Ataque" },
    { id: "infantry", icon: "🪖", fallbackIcon: "I", label: "Infantaria", category: "Ataque" },
    { id: "objective", icon: "🏴", fallbackIcon: "O", label: "Objetivo", category: "Ataque" },
    // LOGÍSTICA
    { id: "logistics", icon: "📦", fallbackIcon: "L", label: "Logística", category: "Logística" },
    { id: "convoy", icon: "🚛", fallbackIcon: "C", label: "Comboio", category: "Logística" },
    { id: "fuel", icon: "⛽", fallbackIcon: "F", label: "Combustível", category: "Logística" },
    { id: "hospital", icon: "🏥", fallbackIcon: "H", label: "Hospital", category: "Logística" },
    { id: "rendezvous", icon: "📍", fallbackIcon: "R", label: "Encontro", category: "Logística" },
    // INFRAESTRUTURA
    { id: "production", icon: "🏭", fallbackIcon: "P", label: "Produção", category: "Infraestrutura" },
    { id: "bridge", icon: "🌉", fallbackIcon: "=", label: "Ponte", category: "Infraestrutura" },
    { id: "port", icon: "🚢", fallbackIcon: "W", label: "Porto", category: "Infraestrutura" },
    { id: "train", icon: "🚂", fallbackIcon: "R", label: "Ferrovia", category: "Infraestrutura" },
    { id: "construction", icon: "🛠", fallbackIcon: "M", label: "Construção", category: "Infraestrutura" },
    // UTILIDADES
    { id: "danger", icon: "⚠", fallbackIcon: "!", label: "Perigo", category: "Utilidades" },
    { id: "observation", icon: "🛰", fallbackIcon: "S", label: "Observação", category: "Utilidades" },
    { id: "communication", icon: "📡", fallbackIcon: "Y", label: "Comunicação", category: "Utilidades" },
    { id: "mining", icon: "⛏", fallbackIcon: "M", label: "Mineração", category: "Utilidades" }
];

function getSymbols() {
    return symbols;
}
