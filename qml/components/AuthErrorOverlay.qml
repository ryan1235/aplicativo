import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: root
    
    // Properties passed from parent
    property bool errorVisible: false
    property string errorCategory: ""
    property string errorMessage: ""
    property string blockedReason: ""
    property string blockedAt: ""
    property int currentLevel: 0
    property int requiredLevel: 0
    
    // Signals
    signal logoutClicked()
    signal retryClicked()
    signal signinClicked()
    signal goBackClicked()
    signal closeAppClicked()

    visible: errorVisible
    anchors.fill: parent
    z: 9999

    function tr(key) {
        if (typeof i18nController !== "undefined") {
            i18nController.revision
            return i18nController.t(key)
        }
        return key
    }

    // Consume mouse events
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.AllButtons
        onWheel: (wheel) => wheel.accepted = true
    }

    // Background Overlay
    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(settingsController.backgroundColor.r, settingsController.backgroundColor.g, settingsController.backgroundColor.b, 0.95)
    }

    // Main Container
    Rectangle {
        id: cardContainer
        width: Math.min(parent.width - 40, 500)
        height: mainColumn.implicitHeight + 60
        anchors.centerIn: parent
        color: settingsController.surfaceColor
        radius: 18
        border.color: categoryBorderColor()
        border.width: 1

        MultiEffect {
            source: cardContainer
            anchors.fill: cardContainer
            shadowEnabled: true
            shadowBlur: 20
            shadowColor: Qt.rgba(0, 0, 0, 0.5)
            shadowVerticalOffset: 10
            autoPaddingEnabled: true
        }

        ColumnLayout {
            id: mainColumn
            anchors.fill: parent
            anchors.margins: 30
            spacing: 20

            // Icon
            Item {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 64
                Layout.preferredHeight: 64
                
                Rectangle {
                    anchors.fill: parent
                    radius: 32
                    color: categoryPanelColor()
                    
                    Text {
                        anchors.centerIn: parent
                        text: categoryIcon()
                        font.pixelSize: 32
                        color: categoryColor()
                    }
                }
            }

            // Title
            Text {
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                text: getTitle()
                color: settingsController.textColor
                font.pixelSize: 24
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            // Body Message
            Text {
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                text: getBody()
                color: settingsController.mutedTextColor
                font.pixelSize: 15
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            // Detail Panel (Conditional)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: detailLayout.implicitHeight + 20
                color: settingsController.backgroundColor
                radius: 10
                visible: hasDetails()
                border.color: settingsController.borderColor
                border.width: 1

                GridLayout {
                    id: detailLayout
                    anchors.fill: parent
                    anchors.margins: 10
                    columns: 2
                    rowSpacing: 8
                    columnSpacing: 10

                    // Blocked details
                    Text {
                        visible: root.errorCategory === "BLOCKED"
                        text: tr("error.auth.blocked.reason_label") + ":"
                        color: settingsController.mutedTextColor
                        font.pixelSize: 13
                        font.bold: true
                    }
                    Text {
                        visible: root.errorCategory === "BLOCKED"
                        text: root.blockedReason
                        color: settingsController.textColor
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    Text {
                        visible: root.errorCategory === "BLOCKED" && root.blockedAt !== ""
                        text: tr("error.auth.blocked.date_label") + ":"
                        color: settingsController.mutedTextColor
                        font.pixelSize: 13
                        font.bold: true
                    }
                    Text {
                        visible: root.errorCategory === "BLOCKED" && root.blockedAt !== ""
                        text: root.blockedAt
                        color: settingsController.textColor
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    // Access Denied Details
                    Text {
                        visible: root.errorCategory === "ACCESS_DENIED" || root.errorCategory === "PERMISSION"
                        text: tr("Nível de Acesso") + ":"
                        color: settingsController.mutedTextColor
                        font.pixelSize: 13
                        font.bold: true
                    }
                    Text {
                        visible: root.errorCategory === "ACCESS_DENIED" || root.errorCategory === "PERMISSION"
                        text: root.currentLevel + " → Requerido: " + root.requiredLevel
                        color: settingsController.textColor
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    // Error Message fallback detail
                    Text {
                        visible: root.errorCategory === "UNKNOWN"
                        text: "Mensagem:"
                        color: settingsController.mutedTextColor
                        font.pixelSize: 13
                        font.bold: true
                    }
                    Text {
                        visible: root.errorCategory === "UNKNOWN"
                        text: root.errorMessage
                        color: settingsController.textColor
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }

            Item { Layout.preferredHeight: 10; Layout.fillWidth: true } // Spacer

            // Actions
            RowLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                spacing: 15

                // Secondary/Go Back Button
                PrimaryButton {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    text: tr("error.auth.btn.go_back")
                    visible: root.errorCategory === "PERMISSION"
                    fill: settingsController.controlColor
                    hoverFill: settingsController.controlHoverColor
                    textFill: settingsController.textColor
                    onClicked: root.goBackClicked()
                }

                // Retry Button
                PrimaryButton {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    text: tr("error.auth.btn.retry")
                    visible: root.errorCategory === "ACCESS_DENIED" || root.errorCategory === "UNKNOWN"
                    fill: settingsController.accentColor
                    hoverFill: settingsController.accentHoverColor
                    textFill: settingsController.textColor
                    onClicked: root.retryClicked()
                }

                // Sign in with Discord Button
                PrimaryButton {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    text: tr("error.auth.btn.signin_discord")
                    visible: root.errorCategory === "REAUTH"
                    fill: settingsController.infoColor
                    hoverFill: settingsController.controlHoverColor
                    textFill: settingsController.textColor
                    onClicked: root.signinClicked()
                }

                // Logout Button
                PrimaryButton {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    text: tr("error.auth.btn.logout")
                    visible: root.errorCategory !== "PERMISSION"
                    fill: settingsController.controlColor
                    hoverFill: settingsController.controlHoverColor
                    textFill: settingsController.textColor
                    onClicked: root.logoutClicked()
                }

                // Close App Button
                PrimaryButton {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    text: tr("error.auth.btn.close_app")
                    visible: root.errorCategory === "BLOCKED"
                    fill: settingsController.dangerColor
                    hoverFill: settingsController.dangerHoverColor
                    textFill: settingsController.textColor
                    onClicked: root.closeAppClicked()
                }
            }
            
            // Support text
            Text {
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                text: root.errorCategory === "BLOCKED" ? tr("error.auth.blocked.contact_support") : ""
                visible: root.errorCategory === "BLOCKED"
                color: settingsController.mutedTextColor
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }
    }

    // Helper functions
    function categoryColor() {
        switch(root.errorCategory) {
            case "BLOCKED": return settingsController.dangerColor;
            case "NOT_FOUND": return settingsController.dangerColor;
            case "ACCESS_DENIED": return settingsController.warningColor || settingsController.accentColor;
            case "PERMISSION": return settingsController.warningColor || settingsController.accentColor;
            case "REAUTH": return settingsController.infoColor;
            default: return settingsController.mutedTextColor;
        }
    }

    function categoryBorderColor() {
        var c = categoryColor();
        return Qt.rgba(c.r, c.g, c.b, 0.3);
    }

    function categoryPanelColor() {
        var c = categoryColor();
        return Qt.rgba(c.r, c.g, c.b, 0.1);
    }

    function categoryIcon() {
        switch(root.errorCategory) {
            case "BLOCKED": return "🚫";
            case "ACCESS_DENIED": return "✋";
            case "PERMISSION": return "🔒";
            case "REAUTH": return "🔑";
            case "NOT_FOUND": return "❓";
            default: return "⚠️";
        }
    }

    function getTitle() {
        switch(root.errorCategory) {
            case "BLOCKED": return tr("error.auth.blocked.title");
            case "ACCESS_DENIED": return tr("error.auth.denied.title");
            case "REAUTH": return tr("error.auth.reauth.title");
            case "PERMISSION": return tr("error.auth.permission.title");
            case "NOT_FOUND": return tr("error.auth.not_found.title");
            default: return tr("error.auth.unknown.title");
        }
    }

    function getBody() {
        switch(root.errorCategory) {
            case "BLOCKED": return tr("error.auth.blocked.body");
            case "ACCESS_DENIED": return tr("error.auth.denied.body");
            case "REAUTH": return tr("error.auth.reauth.body");
            case "PERMISSION": return tr("error.auth.permission.body");
            case "NOT_FOUND": return tr("error.auth.not_found.body");
            default: return tr("error.auth.unknown.body");
        }
    }

    function hasDetails() {
        if (root.errorCategory === "BLOCKED" && root.blockedReason !== "") return true;
        if (root.errorCategory === "ACCESS_DENIED" && root.currentLevel !== 0) return true;
        if (root.errorCategory === "PERMISSION" && root.currentLevel !== 0) return true;
        if (root.errorCategory === "UNKNOWN" && root.errorMessage !== "") return true;
        return false;
    }
}
