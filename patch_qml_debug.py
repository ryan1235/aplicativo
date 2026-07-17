import re

with open('c:/Users/ryanl/OneDrive/Desktop/aplicativo/qml/components/MapView.qml', 'r', encoding='utf-8') as f:
    content = f.read()

debug_props = """        property string jsonOutput: ""
        property int serverVersion: 0
        property int pendingQueueSize: 0
        property string latestLogType: ""
"""
content = content.replace('        property string jsonOutput: ""', debug_props)

old_logAppended = """        function onLogAppended(logStr) {
            try {
                var parsed = JSON.parse(logStr);
                logStr = JSON.stringify(parsed, null, 2);
            } catch (e) {}
            var currentLog = jsonDebugWindow.jsonOutput || "";
            jsonDebugWindow.jsonOutput = logStr + "\\n\\n" + currentLog.substring(0, 10000);
        }"""

new_logAppended = """        function onLogAppended(logStr) {
            try {
                var parsed = JSON.parse(logStr);
                
                if (parsed.serverVersion !== undefined) jsonDebugWindow.serverVersion = parsed.serverVersion;
                if (parsed.action !== undefined) jsonDebugWindow.latestLogType = parsed.action;
                if (parsed.category === 'SINCRONIZAÇÃO' && parsed.action === 'queue_event') {
                    jsonDebugWindow.pendingQueueSize += 1;
                }
                if (parsed.action === 'event_ack') {
                    jsonDebugWindow.pendingQueueSize = Math.max(0, jsonDebugWindow.pendingQueueSize - 1);
                }
                if (parsed.action === 'snapshot_download' || parsed.action === 'connect') {
                    jsonDebugWindow.pendingQueueSize = 0;
                }
                
                logStr = JSON.stringify(parsed, null, 2);
            } catch (e) {}
            var currentLog = jsonDebugWindow.jsonOutput || "";
            jsonDebugWindow.jsonOutput = logStr + "\\n\\n" + currentLog.substring(0, 10000);
        }"""

content = content.replace(old_logAppended, new_logAppended)

# Add smart debug panel UI above TextEdit
old_ui = """                TextEdit {
                    id: jsonTextEdit
                    text: jsonDebugWindow.jsonOutput"""

new_ui = """                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Text { text: "Ver: " + jsonDebugWindow.serverVersion; color: "#00ff00"; font.bold: true }
                    Text { text: "Queue: " + jsonDebugWindow.pendingQueueSize; color: jsonDebugWindow.pendingQueueSize > 0 ? "#ffaa00" : "#00ff00"; font.bold: true }
                    Text { text: "Last: " + jsonDebugWindow.latestLogType; color: "#aaaaaa"; Layout.fillWidth: true; elide: Text.ElideRight }
                }
                Rectangle { height: 1; Layout.fillWidth: true; color: "#333333" }
                
                TextEdit {
                    id: jsonTextEdit
                    text: jsonDebugWindow.jsonOutput"""

content = content.replace(old_ui, new_ui)

with open('c:/Users/ryanl/OneDrive/Desktop/aplicativo/qml/components/MapView.qml', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch applied to MapView.qml")
