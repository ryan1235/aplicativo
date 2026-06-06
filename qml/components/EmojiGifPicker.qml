import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root
    width: 320
    height: 420
    modal: false
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    
    signal emojiSelected(string emoji)
    signal gifSelected(string gifUrl)
    
    property int currentTab: 0 
    property var gifsModel: ListModel {}
    property var emojiModel: ListModel {}
    
    property var allEmojis: [
        {char: "😀", name: "smile feliz"}, {char: "😁", name: "smile feliz"}, {char: "😂", name: "laugh rir chorando"},
        {char: "🤣", name: "laugh rir chorando rofl"}, {char: "😊", name: "smile feliz"}, {char: "😍", name: "love amor apaixonado"},
        {char: "🥰", name: "love amor"}, {char: "😎", name: "cool oculos"}, {char: "🤔", name: "think pensando"},
        {char: "😐", name: "neutral serio"}, {char: "🙄", name: "roll eyes revirando"}, {char: "😥", name: "sad triste chorando"},
        {char: "😭", name: "cry chorando"}, {char: "😡", name: "angry irritado raiva"}, {char: "👍", name: "like joinha ok yes"},
        {char: "👎", name: "dislike nao no"}, {char: "👏", name: "clap palmas"}, {char: "🙌", name: "hands maos amem"},
        {char: "🦊", name: "fox raposa foxhole"}, {char: "💣", name: "bomb bomba"}, {char: "🔫", name: "gun arma tiro"},
        {char: "🔪", name: "knife faca"}, {char: "🛡️", name: "shield escudo def"}, {char: "⚔️", name: "sword espada ataque"},
        {char: "🪖", name: "helmet capacete soldado"}, {char: "🏥", name: "hospital medic"}, {char: "🚑", name: "ambulance ambulancia"},
        {char: "🔥", name: "fire fogo chama"}, {char: "✨", name: "sparkles brilho"}, {char: "❤️", name: "heart coracao amor"},
        {char: "💀", name: "skull caveira morte dead"}, {char: "👽", name: "alien"}, {char: "💩", name: "poop coco"},
        {char: "🤡", name: "clown palhaco"}, {char: "🐶", name: "dog cachorro"}, {char: "🐱", name: "cat gato"},
        {char: "🚗", name: "car carro logi"}, {char: "🚚", name: "truck caminhao logi"}, {char: "📦", name: "box caixa logi supplies"}
    ]
    
    function filterEmojis(query) {
        emojiModel.clear()
        var q = query.toLowerCase()
        for(var i=0; i<allEmojis.length; i++) {
            if (q === "" || allEmojis[i].name.indexOf(q) !== -1) {
                emojiModel.append({"emoji": allEmojis[i].char})
            }
        }
    }

    function searchGifs(query) {
        gifsModel.clear()
        var xhr = new XMLHttpRequest();
        var url = "https://g.tenor.com/v1/search?q=" + encodeURIComponent(query) + "&key=LIVDSRZULELA&limit=30";
        if (query === "") {
            url = "https://g.tenor.com/v1/search?q=foxhole&key=LIVDSRZULELA&limit=30";
        }
        xhr.open("GET", url);
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    var response = JSON.parse(xhr.responseText);
                    var results = response.results;
                    for (var i = 0; i < results.length; i++) {
                        var gifUrl = results[i].media[0].tinygif.url; 
                        var fullUrl = results[i].media[0].gif.url; 
                        gifsModel.append({ "previewUrl": gifUrl, "fullUrl": fullUrl });
                    }
                }
            }
        }
        xhr.send();
    }

    onOpened: {
        if (currentTab === 1 && gifsModel.count === 0) {
            searchGifs(""); 
        }
        if (emojiModel.count === 0) {
            filterEmojis("");
        }
    }
    
    background: Rectangle {
        radius: 12
        color: "#111c31"
        border.color: "#24486d"
        border.width: 1
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 12
        
        RowLayout {
            Layout.fillWidth: true
            spacing: 4
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                background: Rectangle {
                    color: root.currentTab === 0 ? "#1d3353" : "transparent"
                    radius: 6
                }
                contentItem: Text {
                    text: "Emojis"
                    color: root.currentTab === 0 ? "#5eead4" : "#99abc4"
                    font.bold: root.currentTab === 0
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: root.currentTab = 0
            }
            Button {
                Layout.fillWidth: true
                Layout.preferredHeight: 32
                background: Rectangle {
                    color: root.currentTab === 1 ? "#1d3353" : "transparent"
                    radius: 6
                }
                contentItem: Text {
                    text: "GIFs"
                    color: root.currentTab === 1 ? "#5eead4" : "#99abc4"
                    font.bold: root.currentTab === 1
                    font.pixelSize: 13
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }
                onClicked: {
                    root.currentTab = 1
                    if (gifsModel.count === 0) searchGifs("")
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.currentTab === 0
            spacing: 8

            TextField {
                id: emojiSearch
                Layout.fillWidth: true
                placeholderText: "Pesquisar emojis..."
                color: "#edf6ff"
                background: Rectangle { radius: 7; color: "#0e1a2d"; border.color: "#2d496f" }
                onTextChanged: root.filterEmojis(text)
            }

            GridView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                cellWidth: 40
                cellHeight: 40
                clip: true
                model: root.emojiModel
                delegate: Rectangle {
                    width: 36
                    height: 36
                    color: mouseEmoji.containsMouse ? "#1d3353" : "transparent"
                    radius: 6
                    Text {
                        anchors.centerIn: parent
                        text: model.emoji
                        font.pixelSize: 22
                    }
                    MouseArea {
                        id: mouseEmoji
                        anchors.fill: parent
                        hoverEnabled: true
                        onClicked: root.emojiSelected(model.emoji)
                    }
                }
                ScrollBar.vertical: ScrollBar {
                    active: true
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: root.currentTab === 1
            spacing: 8
            
            TextField {
                id: gifSearch
                Layout.fillWidth: true
                placeholderText: "Pesquisar GIFs no Tenor..."
                color: "#edf6ff"
                background: Rectangle { radius: 7; color: "#0e1a2d"; border.color: "#2d496f" }
                onAccepted: root.searchGifs(text)
            }
            
            GridView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                cellWidth: 140
                cellHeight: 110
                clip: true
                model: root.gifsModel
                delegate: Rectangle {
                    width: 136
                    height: 104
                    color: "#0e1a2d"
                    radius: 8
                    clip: true
                    
                    AnimatedImage {
                        anchors.fill: parent
                        source: model.previewUrl
                        fillMode: Image.PreserveAspectCrop
                        cache: true
                        asynchronous: true
                        playing: root.currentTab === 1 && root.visible
                    }
                    
                    MouseArea {
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.gifSelected(model.fullUrl)
                            root.close()
                        }
                        Rectangle {
                            anchors.fill: parent
                            color: "#ffffff"
                            opacity: parent.containsMouse ? 0.1 : 0
                        }
                    }
                }
                ScrollBar.vertical: ScrollBar {
                    active: true
                }
            }
        }
    }
}
