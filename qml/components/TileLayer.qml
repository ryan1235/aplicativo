import QtQuick
import QtQuick.Controls

Item {
    id: tileLayerRoot
    
    property string baseUrl: ""
    property string fallbackUrl: ""
    property string tileUrlMode: "icons" // "icons" | "labels"
    property int tileSize: 256
    property int layerZoom: 2
    
    property real centerX: 0
    property real centerY: 0
    
    property bool isBackground: false
    property bool freezeCenter: false
    property real logicalCenterX: centerX
    property real logicalCenterY: centerY
    
    onCenterXChanged: { if (!freezeCenter) logicalCenterX = centerX; }
    onCenterYChanged: { if (!freezeCenter) logicalCenterY = centerY; }
    
    // View dimensions must be the actual screen size (usually passed down from MapView)
    // We traverse up to find the root MapView size, or default to a reasonable screen size
    property real viewWidth: parent && parent.parent ? parent.parent.width : 1920
    property real viewHeight: parent && parent.parent ? parent.parent.height : 1080
    
    property int viewLeftTile: Math.floor((logicalCenterX - (viewWidth / 2)) / tileSize)
    property int viewTopTile: Math.floor((logicalCenterY - (viewHeight / 2)) / tileSize)
    
    property int poolCols: Math.ceil(viewWidth / tileSize) + 2
    property int poolRows: Math.ceil(viewHeight / tileSize) + 2
    property int poolCount: poolCols * poolRows
    
    x: (viewWidth / 2) - centerX
    y: (viewHeight / 2) - centerY
    width: Math.pow(2, layerZoom) * tileSize
    height: width

    property bool hideTiles: false
    property int loadingCount: 0
    property bool isLoaded: loadingCount === 0

    Repeater {
        id: poolRepeater
        model: poolCount

        delegate: Loader {
            id: tileLoader
            property int colIndex: index % poolCols
            property int rowIndex: Math.floor(index / poolCols)
            
            property int tileX: viewLeftTile + ((colIndex - (viewLeftTile % poolCols) + poolCols) % poolCols)
            property int tileY: viewTopTile + ((rowIndex - (viewTopTile % poolRows) + poolRows) % poolRows)
            property int maxTileIndex: Math.pow(2, tileLayerRoot.layerZoom) - 1
            
            property bool isValidTile: tileX >= 0 && tileX <= maxTileIndex && tileY >= 0 && tileY <= maxTileIndex
            
            x: tileX * tileLayerRoot.tileSize
            y: tileY * tileLayerRoot.tileSize
            width: tileLayerRoot.tileSize
            height: tileLayerRoot.tileSize
            
            active: isValidTile && !tileLayerRoot.hideTiles
            
            sourceComponent: Image {
                source: {
                    if (typeof mapController !== "undefined" && mapController) {
                        if (tileLayerRoot.tileUrlMode === "labels" && mapController.getLabelsTileUrl) {
                            return mapController.getLabelsTileUrl(tileLayerRoot.layerZoom, tileLoader.tileX, tileLoader.tileY);
                        }
                        if (mapController.getTileUrl) {
                            return mapController.getTileUrl(tileLayerRoot.layerZoom, tileLoader.tileX, tileLoader.tileY);
                        }
                    }
                    return tileLayerRoot.baseUrl.replace("{z}", tileLayerRoot.layerZoom).replace("{x}", tileLoader.tileX).replace("{y}", tileLoader.tileY);
                }
                
                asynchronous: true // Always async for smoother UI
                cache: false
                sourceSize.width: tileLayerRoot.tileSize
                sourceSize.height: tileLayerRoot.tileSize
                fillMode: Image.PreserveAspectFit
                visible: status === Image.Ready && source.toString().length > 0
                
                property bool isLoading: status === Image.Loading
                onIsLoadingChanged: {
                    if (isLoading) {
                        tileLayerRoot.loadingCount++;
                    } else {
                        tileLayerRoot.loadingCount--;
                    }
                }
                Component.onDestruction: {
                    if (isLoading) tileLayerRoot.loadingCount--;
                }
            }
        }
    }
}
