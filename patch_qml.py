import re
import time

with open('c:/Users/ryanl/OneDrive/Desktop/aplicativo/qml/components/MapView.qml', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """root.drawings = newDrawings;
                            if (typeof mapSessionController !== 'undefined') {
                                if (newDrawings.length > 0) {
                                    var lastAdded = newDrawings[newDrawings.length - 1];
                                    mapSessionController.pushEvent("add_drawing", "draw_" + Date.now(), JSON.stringify(lastAdded));
                                } else {
                                    mapSessionController.pushEvent("clear_all", "all", "{}");
                                }
                            }"""
                            
content = content.replace("root.drawings = newDrawings;", replacement)
content = content.replace("root.drawings = currentDrawings;", replacement.replace("newDrawings", "currentDrawings"))

replacement_clear = """root.drawings = [];
                            if (typeof mapSessionController !== 'undefined') {
                                mapSessionController.pushEvent("clear_all", "all", "{}");
                            }"""
content = content.replace("root.drawings = [];", replacement_clear)

with open('c:/Users/ryanl/OneDrive/Desktop/aplicativo/qml/components/MapView.qml', 'w', encoding='utf-8') as f:
    f.write(content)
