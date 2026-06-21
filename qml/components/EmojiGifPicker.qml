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

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }
    
    property var allEmojis: [
        {char: "ðŸ˜€", name: "smile feliz"}, {char: "ðŸ˜", name: "smile feliz"}, {char: "ðŸ˜‚", name: "laugh rir chorando"},
        {char: "ðŸ¤£", name: "laugh rir chorando rofl"}, {char: "ðŸ˜Š", name: "smile feliz"}, {char: "ðŸ˜", name: "love amor apaixonado"},
        {char: "ðŸ¥°", name: "love amor"}, {char: "ðŸ˜Ž", name: "cool oculos"}, {char: "ðŸ¤”", name: "think pensando"},
        {char: "ðŸ˜", name: "neutral serio"}, {char: "ðŸ™„", name: "roll eyes revirando"}, {char: "ðŸ˜¥", name: "sad triste chorando"},
        {char: "ðŸ˜­", name: "cry chorando"}, {char: "ðŸ˜¡", name: "angry irritado raiva"}, {char: "ðŸ‘", name: "like joinha ok yes"},
        {char: "ðŸ‘Ž", name: "dislike nao no"}, {char: "ðŸ‘", name: "clap palmas"}, {char: "ðŸ™Œ", name: "hands maos amem"},
        {char: "ðŸ¦Š", name: "fox raposa foxhole"}, {char: "ðŸ’£", name: "bomb bomba"}, {char: "ðŸ”«", name: "gun arma tiro"},
        {char: "ðŸ”ª", name: "knife faca"}, {char: "ðŸ›¡ï¸", name: "shield escudo def"}, {char: "âš”ï¸", name: "sword espada ataque"},
        {char: "ðŸª–", name: "helmet capacete soldado"}, {char: "ðŸ¥", name: "hospital medic"}, {char: "ðŸš‘", name: "ambulance ambulancia"},
        {char: "ðŸ”¥", name: "fire fogo chama"}, {char: "âœ¨", name: "sparkles brilho"}, {char: "â¤ï¸", name: "heart coracao amor"},
        {char: "ðŸ’€", name: "skull caveira morte dead"}, {char: "ðŸ‘½", name: "alien"}, {char: "ðŸ’©", name: "poop coco"},
        {char: "ðŸ¤¡", name: "clown palhaco"}, {char: "ðŸ¶", name: "dog cachorro"}, {char: "ðŸ±", name: "cat gato"},
        {char: "ðŸš—", name: "car carro logi"}, {char: "ðŸšš", name: "truck caminhao logi"}, {char: "ðŸ“¦", name: "box caixa logi supplies"}
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
        var url = "https://g.tenor.com/v1/search?q=" + encodeURIComponent(query) + "&key=LIVDSRZULELA&limit=18";
        if (query === "") {
            url = "https://g.tenor.com/v1/search?q=foxhole&key=LIVDSRZULELA&limit=18";
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
        color: settingsController.surfaceColor
        border.color: settingsController.borderColor
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
                    color: root.currentTab === 0 ? settingsController.controlColor : "transparent"
                    radius: 6
                }
                contentItem: Text {
                    text: tr("home.chat.emoji")
                    color: root.currentTab === 0 ? settingsController.accentColor : settingsController.mutedTextColor
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
                    color: root.currentTab === 1 ? settingsController.controlColor : "transparent"
                    radius: 6
                }
                contentItem: Text {
                    text: tr("home.chat.gifs")
                    color: root.currentTab === 1 ? settingsController.accentColor : settingsController.mutedTextColor
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
                placeholderText: tr("home.chat.search_emojis")
                color: settingsController.textColor
                background: Rectangle { radius: 7; color: settingsController.surfaceAltColor; border.color: settingsController.controlHoverColor }
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
                    color: mouseEmoji.containsMouse ? settingsController.controlColor : "transparent"
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
                placeholderText: tr("home.chat.search_gifs_tenor")
                color: settingsController.textColor
                background: Rectangle { radius: 7; color: settingsController.surfaceAltColor; border.color: settingsController.controlHoverColor }
                onAccepted: root.searchGifs(text)
            }
            
            GridView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                cellWidth: 140
                cellHeight: 110
                clip: true
                reuseItems: true
                model: root.gifsModel
                delegate: Rectangle {
                    width: 136
                    height: 104
                    color: settingsController.surfaceAltColor
                    radius: 8
                    clip: true
                    
                    AnimatedImage {
                        anchors.fill: parent
                        source: model.previewUrl
                        fillMode: Image.PreserveAspectCrop
                        cache: false
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
                            color: settingsController.textColor
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


