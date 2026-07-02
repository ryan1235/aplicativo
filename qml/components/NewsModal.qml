import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Popup {
    id: root
    width: Math.min(920, parent.width - 56)
    height: Math.min(760, parent.height - 56)
    x: Math.round((parent.width - width) / 2)
    y: Math.round((parent.height - height) / 2)
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    
    property var newsItem: null

    function tr(key) {
        i18nController.revision
        return i18nController.t(key)
    }

    function newsDate(value) {
        if (!value)
            return ""
        var date = new Date(value)
        if (isNaN(date.getTime()))
            return ""
        var dateMask = i18nController.language === "en" ? "MM/dd/yyyy" : "dd/MM/yyyy"
        return Qt.formatDateTime(date, dateMask + " HH:mm")
    }

    function newsAge(value) {
        if (!value)
            return ""
        var date = new Date(value)
        if (isNaN(date.getTime()))
            return ""
        var seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000))
        if (seconds < 60)
            return tr("home.news.just_now")
        var minutes = Math.floor(seconds / 60)
        if (minutes < 60)
            return minutes + " " + tr(minutes === 1 ? "home.news.minute_ago" : "home.news.minutes_ago")
        var hours = Math.floor(minutes / 60)
        if (hours < 24)
            return hours + " " + tr(hours === 1 ? "home.news.hour_ago" : "home.news.hours_ago")
        var days = Math.floor(hours / 24)
        return days + " " + tr(days === 1 ? "home.news.day_ago" : "home.news.days_ago")
    }

    function newsCategory() {
        var raw = String((newsItem && newsItem.type) || "general").toLowerCase()
        var normalized = raw.replace(/[^a-z0-9_-]+/g, "-")
        var key = "home.news.category." + normalized
        var translated = tr(key)
        if (translated !== key)
            return translated
        return (newsItem && newsItem.category) ? newsItem.category : raw
    }

    function metaText() {
        if (!newsItem)
            return ""
        var pieces = []
        pieces.push(tr("home.news.by") + " " + (newsItem.authorName || "GG Coalition"))
        var ageText = newsAge(newsItem.date)
        if (ageText)
            pieces.push(ageText)
        var dateText = newsDate(newsItem.date)
        if (dateText)
            pieces.push(dateText)
        pieces.push(String(newsItem.viewCount || 0) + " " + tr("home.news.views"))
        return pieces.join("  |  ")
    }

    function blocksModel() {
        if (newsItem && newsItem.contentBlocks && newsItem.contentBlocks.length)
            return newsItem.contentBlocks
            
        var rawHtml = "";
        if (newsItem && newsItem.bodyHtml) {
            rawHtml = newsItem.bodyHtml;
        } else if (newsItem && newsItem.body) {
            rawHtml = newsItem.body;
        }
        
        if (rawHtml) {
            var blocks = [];
            var imgRegex = /<img\b([^>]*)>/gi;
            var lastIndex = 0;
            var match;
            
            while ((match = imgRegex.exec(rawHtml)) !== null) {
                if (match.index > lastIndex) {
                    blocks.push({ "type": "rich", "html": rawHtml.substring(lastIndex, match.index) });
                }
                
                var inner = match[1];
                var srcMatch = inner.match(/\bsrc\s*=\s*(['"])(.*?)\1/i);
                var altMatch = inner.match(/\balt\s*=\s*(['"])(.*?)\1/i);
                var widthMatch = inner.match(/\bwidth\s*=\s*(['"]?)(\d+)\1/i);
                var w = widthMatch ? parseInt(widthMatch[2]) : 0;
                
                if (w > 0 && w <= 150) {
                    // Small images / icons remain inline
                    blocks.push({ "type": "rich", "html": match[0] });
                } else {
                    blocks.push({ 
                        "type": "image", 
                        "src": srcMatch ? srcMatch[2] : "", 
                        "alt": altMatch ? altMatch[2] : "" 
                    });
                }
                
                lastIndex = imgRegex.lastIndex;
            }
            
            if (lastIndex < rawHtml.length) {
                blocks.push({ "type": "rich", "html": rawHtml.substring(lastIndex) });
            }
            
            var merged = [];
            for (var i = 0; i < blocks.length; i++) {
                if (blocks[i].type === "rich" && merged.length > 0 && merged[merged.length - 1].type === "rich") {
                    merged[merged.length - 1].html += blocks[i].html;
                } else {
                    merged.push(blocks[i]);
                }
            }
            return merged.length ? merged : [{ "type": "rich", "html": rawHtml }];
        }
        
        return []
    }
    
    background: Rectangle {
        color: settingsController.surfaceAltColor
        border.color: settingsController.borderColor
        radius: 8
    }

    Overlay.modal: Rectangle {
        color: settingsController.scrimColor
        opacity: 0.60
    }

    onOpened: {
        if (newsItem && newsItem.id) {
            newsController.registerView(newsItem.id)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 30
        spacing: 18

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            Rectangle {
                Layout.preferredHeight: 28
                Layout.minimumWidth: modalCategoryText.implicitWidth + 22
                radius: 14
                color: settingsController.surfaceRaisedColor
                border.color: settingsController.accentHoverColor

                Text {
                    id: modalCategoryText
                    anchors.centerIn: parent
                    text: root.newsCategory()
                    color: settingsController.accentColor
                    font.family: "Segoe UI"
                    font.pixelSize: 12
                    font.bold: true
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.metaText()
                color: settingsController.secondaryTextColor
                font.family: "Segoe UI"
                font.pixelSize: 12
                font.bold: true
                elide: Text.ElideRight
                visible: text !== ""
            }

            PrimaryButton {
                Layout.preferredWidth: 96
                text: tr("toolbar.close")
                fill: settingsController.controlColor
                hoverFill: settingsController.controlHoverColor
                textFill: settingsController.textColor
                onClicked: root.close()
            }
        }

        Text {
            Layout.fillWidth: true
            text: newsItem ? (newsItem.title || "News") : ""
            color: settingsController.textColor
            font.family: "Segoe UI"
            font.pixelSize: 30
            font.bold: true
            lineHeight: 0.95
            wrapMode: Text.WordWrap
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: settingsController.borderColor
        }

        ScrollView {
            id: articleScroll
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            contentWidth: availableWidth
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            Column {
                id: articleColumn
                width: Math.max(0, articleScroll.availableWidth - 16)
                spacing: 14

                Repeater {
                    model: root.blocksModel()

                    delegate: Loader {
                        property var block: modelData
                        width: articleColumn.width
                        height: item ? item.implicitHeight : 0
                        sourceComponent: block.type === "image"
                            ? imageBlock
                            : block.type === "heading"
                                ? headingBlock
                                : block.type === "quote"
                                    ? quoteBlock
                                    : block.type === "divider"
                                        ? dividerBlock
                                        : richBlock
                        onLoaded: {
                            if (item && typeof item.block !== "undefined")
                                item.block = block
                        }
                    }
                }
            }
        }
    }

    Component {
        id: headingBlock
        Text {
            property var block: ({})
            width: articleColumn.width
            text: block.html || ""
            color: settingsController.textColor
            font.family: "Segoe UI"
            font.pixelSize: block.level === 1 ? 25 : block.level === 2 ? 21 : 18
            font.bold: true
            wrapMode: Text.WordWrap
            textFormat: Text.RichText
            lineHeight: 1.05
        }
    }

    Component {
        id: richBlock
        Text {
            property var block: ({})
            width: articleColumn.width
            text: block.html || ""
            color: settingsController.secondaryTextColor
            font.family: "Segoe UI"
            font.pixelSize: 15
            wrapMode: Text.WordWrap
            textFormat: Text.RichText
            lineHeight: 1.18
            onLinkActivated: Qt.openUrlExternally(link)
        }
    }

    Component {
        id: quoteBlock
        Rectangle {
            property var block: ({})
            width: articleColumn.width
            implicitHeight: quoteText.implicitHeight + 20
            radius: 7
            color: settingsController.surfaceRaisedColor
            border.color: settingsController.borderColor

            Rectangle {
                width: 3
                anchors.left: parent.left
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                color: settingsController.accentColor
            }

            Text {
                id: quoteText
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                anchors.leftMargin: 16
                text: block.html || ""
                color: settingsController.secondaryTextColor
                font.family: "Segoe UI"
                font.pixelSize: 14
                font.italic: true
                wrapMode: Text.WordWrap
                textFormat: Text.RichText
            }
        }
    }

    Component {
        id: dividerBlock
        Rectangle {
            width: articleColumn.width
            implicitHeight: 1
            color: settingsController.borderColor
        }
    }

    Component {
        id: imageBlock
        Column {
            property var block: ({})
            width: articleColumn.width
            spacing: 6

            Rectangle {
                id: imageFrame
                anchors.horizontalCenter: parent.horizontalCenter
                width: Math.min(parent.width, 860)
                implicitHeight: newsImg.status === Image.Ready && newsImg.implicitWidth > 0 
                                ? (width * (newsImg.implicitHeight / newsImg.implicitWidth)) 
                                : (width * 0.5625)
                radius: 8
                color: settingsController.backgroundColor
                border.color: settingsController.borderColor
                clip: true

                Image {
                    id: newsImg
                    anchors.fill: parent
                    anchors.margins: 0
                    source: block.src || ""
                    fillMode: Image.PreserveAspectFit
                    asynchronous: true
                    cache: true
                }
            }

            Text {
                id: imageCaption
                anchors.horizontalCenter: parent.horizontalCenter
                width: imageFrame.width
                horizontalAlignment: Text.AlignHCenter
                text: block.alt || ""
                color: settingsController.disabledTextColor
                font.family: "Segoe UI"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
                visible: text !== ""
            }
        }
    }
}


