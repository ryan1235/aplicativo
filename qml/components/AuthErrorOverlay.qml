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
        color: Qt.rgba(uiTheme.background.r, uiTheme.background.g, uiTheme.background.b, 0.95)
    }

    // Main Container
    Rectangle {
        id: cardContainer
        width: Math.min(parent.width - 40, 500)
        height: mainColumn.implicitHeight + 60
        anchors.centerIn: parent
        color: uiTheme.surface
        radius: uiTheme.cardRadius
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
                color: uiTheme.text
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
                color: uiTheme.mutedText
                font.pixelSize: 15
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            // Detail Panel (Conditional)
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: detailLayout.implicitHeight + 20
                color: uiTheme.background
                radius: uiTheme.cardRadius - 2
                visible: hasDetails()
                border.color: uiTheme.border
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
                        text: i18n.t("error.auth.blocked.reason_label") + ":"
                        color: uiTheme.mutedText
                        font.pixelSize: 13
                        font.bold: true
                    }
                    Text {
                        visible: root.errorCategory === "BLOCKED"
                        text: root.blockedReason
                        color: uiTheme.text
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                    Text {
                        visible: root.errorCategory === "BLOCKED" && root.blockedAt !== ""
                        text: i18n.t("error.auth.blocked.date_label") + ":"
                        color: uiTheme.mutedText
                        font.pixelSize: 13
                        font.bold: true
                    }
                    Text {
                        visible: root.errorCategory === "BLOCKED" && root.blockedAt !== ""
                        text: root.blockedAt
                        color: uiTheme.text
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    // Access Denied Details
                    Text {
                        visible: root.errorCategory === "ACCESS_DENIED" || root.errorCategory === "PERMISSION"
                        text: i18n.t("Nível de Acesso") + ":"
                        color: uiTheme.mutedText
                        font.pixelSize: 13
                        font.bold: true
                    }
                    Text {
                        visible: root.errorCategory === "ACCESS_DENIED" || root.errorCategory === "PERMISSION"
                        text: root.currentLevel + " → Requerido: " + root.requiredLevel
                        color: uiTheme.text
                        font.pixelSize: 13
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }

                    // Error Message fallback detail
                    Text {
                        visible: root.errorCategory === "UNKNOWN"
                        text: "Mensagem:"
                        color: uiTheme.mutedText
                        font.pixelSize: 13
                        font.bold: true
                    }
                    Text {
                        visible: root.errorCategory === "UNKNOWN"
                        text: root.errorMessage
                        color: uiTheme.text
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
                Button {
                    Layout.fillWidth: true
                    text: i18n.t("error.auth.btn.go_back")
                    visible: root.errorCategory === "PERMISSION"
                    onClicked: root.goBackClicked()
                }

                // Retry Button
                Button {
                    Layout.fillWidth: true
                    text: i18n.t("error.auth.btn.retry")
                    visible: root.errorCategory === "ACCESS_DENIED" || root.errorCategory === "UNKNOWN"
                    onClicked: root.retryClicked()
                }

                // Sign in with Discord Button
                Button {
                    Layout.fillWidth: true
                    text: i18n.t("error.auth.btn.signin_discord")
                    visible: root.errorCategory === "REAUTH"
                    onClicked: root.signinClicked()
                }

                // Logout Button
                Button {
                    Layout.fillWidth: true
                    text: i18n.t("error.auth.btn.logout")
                    visible: root.errorCategory !== "PERMISSION"
                    onClicked: root.logoutClicked()
                }

                // Close App Button
                Button {
                    Layout.fillWidth: true
                    text: i18n.t("error.auth.btn.close_app")
                    visible: root.errorCategory === "BLOCKED"
                    onClicked: root.closeAppClicked()
                }
            }
            
            // Support text
            Text {
                Layout.alignment: Qt.AlignHCenter
                Layout.fillWidth: true
                text: root.errorCategory === "BLOCKED" ? i18n.t("error.auth.blocked.contact_support") : ""
                visible: root.errorCategory === "BLOCKED"
                color: uiTheme.mutedText
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }
        }
    }

    // Helper functions
    function categoryColor() {
        switch(root.errorCategory) {
            case "BLOCKED": return uiTheme.danger;
            case "NOT_FOUND": return uiTheme.danger;
            case "ACCESS_DENIED": return uiTheme.warning;
            case "PERMISSION": return uiTheme.warning;
            case "REAUTH": return uiTheme.info;
            default: return uiTheme.mutedText;
        }
    }

    function categoryBorderColor() {
        switch(root.errorCategory) {
            case "BLOCKED": return Qt.rgba(uiTheme.danger.r, uiTheme.danger.g, uiTheme.danger.b, 0.3);
            case "NOT_FOUND": return Qt.rgba(uiTheme.danger.r, uiTheme.danger.g, uiTheme.danger.b, 0.3);
            case "ACCESS_DENIED": return Qt.rgba(uiTheme.warning.r, uiTheme.warning.g, uiTheme.warning.b, 0.3);
            case "PERMISSION": return Qt.rgba(uiTheme.warning.r, uiTheme.warning.g, uiTheme.warning.b, 0.3);
            case "REAUTH": return Qt.rgba(uiTheme.info.r, uiTheme.info.g, uiTheme.info.b, 0.3);
            default: return uiTheme.border;
        }
    }

    function categoryPanelColor() {
        switch(root.errorCategory) {
            case "BLOCKED": return uiTheme.dangerPanel;
            case "NOT_FOUND": return uiTheme.dangerPanel;
            case "ACCESS_DENIED": return uiTheme.accentPanel; // or a warning panel if available
            case "PERMISSION": return uiTheme.accentPanel;
            case "REAUTH": return Qt.rgba(uiTheme.info.r, uiTheme.info.g, uiTheme.info.b, 0.1);
            default: return uiTheme.background;
        }
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
            case "BLOCKED": return i18n.t("error.auth.blocked.title");
            case "ACCESS_DENIED": return i18n.t("error.auth.denied.title");
            case "REAUTH": return i18n.t("error.auth.reauth.title");
            case "PERMISSION": return i18n.t("error.auth.permission.title");
            case "NOT_FOUND": return i18n.t("error.auth.not_found.title");
            default: return i18n.t("error.auth.unknown.title");
        }
    }

    function getBody() {
        switch(root.errorCategory) {
            case "BLOCKED": return i18n.t("error.auth.blocked.body");
            case "ACCESS_DENIED": return i18n.t("error.auth.denied.body");
            case "REAUTH": return i18n.t("error.auth.reauth.body");
            case "PERMISSION": return i18n.t("error.auth.permission.body");
            case "NOT_FOUND": return i18n.t("error.auth.not_found.body");
            default: return i18n.t("error.auth.unknown.body");
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
