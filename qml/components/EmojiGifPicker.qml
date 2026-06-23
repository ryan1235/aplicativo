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
        {char: "\uD83D\uDE00", name: "smile feliz"}, {char: "\uD83D\uDE01", name: "smile feliz"}, {char: "\uD83D\uDE02", name: "laugh rir chorando"},
        {char: "\uD83E\uDD23", name: "laugh rir chorando rofl"}, {char: "\uD83D\uDE0A", name: "smile feliz"}, {char: "\uD83D\uDE0D", name: "love amor apaixonado"},
        {char: "\uD83E\uDD70", name: "love amor"}, {char: "\uD83D\uDE0E", name: "cool oculos"}, {char: "\uD83E\uDD14", name: "think pensando"},
        {char: "\uD83D\uDE10", name: "neutral serio"}, {char: "\uD83D\uDE44", name: "roll eyes revirando"}, {char: "\uD83D\uDE25", name: "sad triste chorando"},
        {char: "\uD83D\uDE2D", name: "cry chorando"}, {char: "\uD83D\uDE21", name: "angry irritado raiva"}, {char: "\uD83D\uDC4D", name: "like joinha ok yes"},
        {char: "\uD83D\uDC4E", name: "dislike nao no"}, {char: "\uD83D\uDC4F", name: "clap palmas"}, {char: "\uD83D\uDE4C", name: "hands maos amem"},
        {char: "\uD83E\uDD8A", name: "fox raposa foxhole"}, {char: "\uD83D\uDCA3", name: "bomb bomba"}, {char: "\uD83D\uDD2B", name: "gun arma tiro"},
        {char: "\uD83D\uDD2A", name: "knife faca"}, {char: "\uD83D\uDEE1\uFE0F", name: "shield escudo def"}, {char: "\u2694\uFE0F", name: "sword espada ataque"},
        {char: "\uD83E\uDE96", name: "helmet capacete soldado"}, {char: "\uD83C\uDFE5", name: "hospital medic"}, {char: "\uD83D\uDE91", name: "ambulance ambulancia"},
        {char: "\uD83D\uDD25", name: "fire fogo chama"}, {char: "\u2728", name: "sparkles brilho"}, {char: "\u2764\uFE0F", name: "heart coracao amor"},
        {char: "\uD83D\uDC80", name: "skull caveira morte dead"}, {char: "\uD83D\uDC7D", name: "alien"}, {char: "\uD83D\uDCA9", name: "poop coco"},
        {char: "\uD83E\uDD21", name: "clown palhaco"}, {char: "\uD83D\uDC36", name: "dog cachorro"}, {char: "\uD83D\uDC31", name: "cat gato"},
        {char: "\uD83D\uDE97", name: "car carro logi"}, {char: "\uD83D\uDE9A", name: "truck caminhao logi"}, {char: "\uD83D\uDCE6", name: "box caixa logi supplies"}
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
                        id: gifPreview
                        anchors.fill: parent
                        source: model.previewUrl
                        fillMode: Image.PreserveAspectCrop
                        cache: false
                        asynchronous: true
                        playing: false
                        function updatePlayback() {
                            playing = root.currentTab === 1 && root.visible && status === Image.Ready
                        }
                        Component.onCompleted: updatePlayback()
                        onStatusChanged: {
                            updatePlayback()
                        }
                        onCurrentFrameChanged: {
                            if (playing && frameCount > 1 && currentFrame >= frameCount - 1)
                                gifPreviewLoop.restart()
                        }
                        Connections {
                            target: root
                            function onCurrentTabChanged() { gifPreview.updatePlayback() }
                            function onVisibleChanged() { gifPreview.updatePlayback() }
                        }
                        Timer {
                            id: gifPreviewLoop
                            interval: 16
                            repeat: false
                            onTriggered: {
                                if (root.currentTab === 1 && root.visible && gifPreview.status === Image.Ready) {
                                    gifPreview.currentFrame = 0
                                    gifPreview.updatePlayback()
                                }
                            }
                        }
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


