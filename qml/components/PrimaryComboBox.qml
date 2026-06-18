import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ComboBox {
    id: control

    // Properties for theming
    property color bgNormal: settingsController.backgroundColor
    property color bgHover: settingsController.surfaceColor
    property color borderNormal: settingsController.borderColor
    property color borderFocus: settingsController.accentColor
    property color textNormal: settingsController.textColor
    property color popupBg: settingsController.surfaceColor
    property color popupBorder: settingsController.borderColor
    property color itemHover: settingsController.accentPanelColor

    function tr(key) {
        i18nController.revision
        return key ? i18nController.t(key) : ""
    }

    implicitWidth: 140
    implicitHeight: 42

    delegate: ItemDelegate {
        id: delegateItem
        property bool isObjectRow: typeof modelData === "object"
        property bool isHeaderRow: isObjectRow && modelData.type === "header"
        property string primaryText: isObjectRow ? (modelData.text || "") : (typeof modelData !== "undefined" ? modelData : "")
        property string secondaryText: isObjectRow ? (modelData.subText || "") : ""
        property string trailingText: isObjectRow ? (modelData.sideTextKey ? control.tr(modelData.sideTextKey) : (modelData.sideText || "")) : ""
        property color trailingColor: isObjectRow && modelData.sideColor ? modelData.sideColor : settingsController.accentColor

        width: control.popup.width
        height: isHeaderRow ? 28 : (secondaryText !== "" || trailingText !== "" ? 44 : 36)
        enabled: isObjectRow ? modelData.type !== "header" : true
        
        text: primaryText
        
        contentItem: Item {
            Text {
                id: primaryLabel
                anchors.left: parent.left
                anchors.leftMargin: delegateItem.isObjectRow && modelData.type === "item" ? 12 : 0
                anchors.right: trailingLabel.visible ? trailingLabel.left : parent.right
                anchors.rightMargin: trailingLabel.visible ? 8 : 0
                y: delegateItem.secondaryText !== "" ? 5 : Math.round((parent.height - height) / 2)
                text: delegateItem.primaryText
                color: delegateItem.isHeaderRow ? settingsController.accentColor : (control.highlightedIndex === index ? control.borderFocus : control.textNormal)
                font.family: "Segoe UI"
                font.pixelSize: delegateItem.isHeaderRow ? 11 : 13
                font.bold: delegateItem.isHeaderRow
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                anchors.left: primaryLabel.left
                anchors.right: parent.right
                anchors.rightMargin: 8
                anchors.top: primaryLabel.bottom
                anchors.topMargin: 1
                visible: delegateItem.secondaryText !== ""
                text: delegateItem.secondaryText
                color: settingsController.mutedTextColor
                font.family: "Segoe UI"
                font.pixelSize: 10
                elide: Text.ElideRight
            }

            Text {
                id: trailingLabel
                anchors.right: parent.right
                anchors.rightMargin: 4
                anchors.verticalCenter: parent.verticalCenter
                visible: delegateItem.trailingText !== ""
                text: delegateItem.trailingText
                color: delegateItem.trailingColor
                font.family: "Segoe UI"
                font.pixelSize: 10
                font.bold: true
                horizontalAlignment: Text.AlignRight
            }
        }
        background: Rectangle {
            color: delegateItem.hovered && delegateItem.enabled ? control.itemHover : "transparent"
            radius: 4
            anchors.fill: parent
            anchors.margins: 2
            
            Behavior on color { ColorAnimation { duration: 100 } }
        }
        highlighted: control.highlightedIndex === index
    }

    indicator: Canvas {
        id: canvas
        x: control.width - width - control.rightPadding
        y: control.topPadding + (control.availableHeight - height) / 2
        width: 12
        height: 7
        contextType: "2d"

        Connections {
            target: control
            function onPressedChanged() { canvas.requestPaint(); }
            function onActiveFocusChanged() { canvas.requestPaint(); }
            function onHoveredChanged() { canvas.requestPaint(); }
        }

        onPaint: {
            context.reset();
            context.moveTo(0, 0);
            context.lineTo(width / 2, height);
            context.lineTo(width, 0);
            context.strokeStyle = control.activeFocus || control.pressed || control.hovered ? control.borderFocus : settingsController.mutedTextColor;
            context.lineWidth = 1.8;
            context.stroke();
        }
    }

    contentItem: Text {
        leftPadding: 14
        rightPadding: 30
        text: control.displayText
        font.family: "Segoe UI"
        font.pixelSize: 13
        font.bold: true
        color: control.textNormal
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        implicitWidth: control.implicitWidth
        implicitHeight: control.implicitHeight
        color: control.hovered ? control.bgHover : control.bgNormal
        border.color: control.activeFocus || control.pressed ? control.borderFocus : control.borderNormal
        border.width: control.activeFocus || control.pressed ? 1.5 : 1
        radius: settingsController.cardRadius
        
        Behavior on border.color { ColorAnimation { duration: 150 } }
        Behavior on color { ColorAnimation { duration: 150 } }
    }

    popup: Popup {
        y: control.height + 6
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 10, 280)
        padding: 5

        enter: Transition {
            NumberAnimation { property: "opacity"; from: 0.0; to: 1.0; duration: 150; easing.type: Easing.OutQuad }
            NumberAnimation { property: "y"; from: control.height - 10; to: control.height + 6; duration: 150; easing.type: Easing.OutBack }
        }

        exit: Transition {
            NumberAnimation { property: "opacity"; from: 1.0; to: 0.0; duration: 100; easing.type: Easing.InQuad }
            NumberAnimation { property: "y"; from: control.height + 6; to: control.height - 5; duration: 100; easing.type: Easing.InQuad }
        }

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex

            ScrollBar.vertical: ScrollBar {
                active: true
                policy: ScrollBar.AsNeeded
                contentItem: Rectangle {
                    implicitWidth: 4
                    radius: 2
                    color: parent.pressed ? control.borderFocus : settingsController.borderColor
                }
            }
        }

        background: Rectangle {
            color: control.popupBg
            border.color: control.popupBorder
            border.width: 1
            radius: settingsController.cardRadius
        }
    }
}

