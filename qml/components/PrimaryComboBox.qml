import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ComboBox {
    id: control

    // Properties for theming
    property color bgNormal: "#07111f"
    property color bgHover: "#0a1526"
    property color borderNormal: "#24486d"
    property color borderFocus: "#5eead4"
    property color textNormal: "#edf6ff"
    property color popupBg: "#0c1524"
    property color popupBorder: "#1d3353"
    property color itemHover: "#1d3353"

    implicitWidth: 140
    implicitHeight: 40

    delegate: ItemDelegate {
        id: delegateItem
        width: control.popup.width
        height: typeof modelData === "object" && modelData.type === "header" ? 28 : 36
        enabled: typeof modelData === "object" ? modelData.type !== "header" : true
        
        text: typeof modelData === "object" ? (modelData.text || "") : (typeof modelData !== "undefined" ? modelData : "")
        
        contentItem: Text {
            text: delegateItem.text
            color: (typeof modelData === "object" && modelData.type === "header") ? "#5eead4" : (control.highlightedIndex === index ? control.borderFocus : control.textNormal)
            font.family: "Segoe UI"
            font.pixelSize: (typeof modelData === "object" && modelData.type === "header") ? 11 : 13
            font.bold: typeof modelData === "object" && modelData.type === "header"
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            leftPadding: (typeof modelData === "object" && modelData.type === "item") ? 12 : 0
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
        width: 10
        height: 6
        contextType: "2d"

        Connections {
            target: control
            function onPressedChanged() { canvas.requestPaint(); }
            function onActiveFocusChanged() { canvas.requestPaint(); }
        }

        onPaint: {
            context.reset();
            context.moveTo(0, 0);
            context.lineTo(width / 2, height);
            context.lineTo(width, 0);
            context.strokeStyle = control.activeFocus || control.pressed ? control.borderFocus : "#99abc4";
            context.lineWidth = 1.5;
            context.stroke();
        }
    }

    contentItem: Text {
        leftPadding: 12
        rightPadding: control.indicator.width + control.spacing
        text: control.displayText
        font.family: "Segoe UI"
        font.pixelSize: 14
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
        radius: 8
        
        Behavior on border.color { ColorAnimation { duration: 150 } }
        Behavior on color { ColorAnimation { duration: 150 } }
    }

    popup: Popup {
        y: control.height + 6
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 240)
        padding: 4

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
                    color: parent.pressed ? control.borderFocus : "#2d496f"
                }
            }
        }

        background: Rectangle {
            color: control.popupBg
            border.color: control.popupBorder
            border.width: 1
            radius: 8
        }
    }
}
