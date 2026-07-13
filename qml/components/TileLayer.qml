import QtQuick
import QtQuick.Controls

Item {
    id: tileLayerRoot
    
    property string baseUrl: ""
    property string fallbackUrl: ""
    property string tileUrlMode: "icons" // "icons" | "labels"
    property int tileSize: 256
    property int layerZoom: 2
    property bool isBackground: false
    property real centerX: 0
    property real centerY: 0
    property bool freezeCenter: false
    
    property bool hasLocalTiles: typeof mapController !== "undefined" && mapController ? mapController.localTilesAvailable : false
    property int localTileCols: hasLocalTiles && typeof mapController !== "undefined" && mapController ? mapController.getLocalTileCols(layerZoom) : 0
    property int localTileRows: hasLocalTiles && typeof mapController !== "undefined" && mapController ? mapController.getLocalTileRows(layerZoom) : 0
    property real fullWidth: hasLocalTiles && typeof mapController !== "undefined" && mapController ? mapController.getLocalTileLevelWidth(layerZoom) : Math.pow(2, layerZoom) * tileSize
    property real fullHeight: hasLocalTiles && typeof mapController !== "undefined" && mapController ? mapController.getLocalTileLevelHeight(layerZoom) : Math.pow(2, layerZoom) * tileSize
    property int lastTileWidth: hasLocalTiles && localTileCols > 0 ? Math.max(0, fullWidth - (localTileCols - 1) * tileSize) : tileSize
    property int lastTileHeight: hasLocalTiles && localTileRows > 0 ? Math.max(0, fullHeight - (localTileRows - 1) * tileSize) : tileSize

    property real logicalCenterX: centerX
    property real logicalCenterY: centerY
    
    Component.onCompleted: {
        logicalCenterX = centerX;
        logicalCenterY = centerY;
    }
    
    onCenterXChanged: { if (!freezeCenter) logicalCenterX = centerX; }
    onCenterYChanged: { if (!freezeCenter) logicalCenterY = centerY; }
    
    property real viewWidth: parent ? parent.width : 1920
    property real viewHeight: parent ? parent.height : 1080
    
    property int viewLeftTile: Math.floor((logicalCenterX - (viewWidth / 2)) / tileSize)
    property int viewTopTile: Math.floor((logicalCenterY - (viewHeight / 2)) / tileSize)
    
    property int poolCols: Math.ceil(viewWidth / tileSize) + 1
    property int poolRows: Math.ceil(viewHeight / tileSize) + 1
    property int poolCount: poolCols * poolRows
    
    x: (viewWidth / 2) - centerX
    y: (viewHeight / 2) - centerY
    width: tileLayerRoot.fullWidth
    height: tileLayerRoot.fullHeight

    property bool hideTiles: false
    property int loadingCount: 0
    property bool isLoaded: loadingCount === 0

    function tileUrlFor(z, tx, ty) {
        if (typeof mapController !== "undefined" && mapController) {
            if (tileLayerRoot.hasLocalTiles) {
                var localUrl = mapController.getLocalTileUrl(z, tx, ty);
                if (localUrl) return localUrl;
            }
            if (tileLayerRoot.tileUrlMode === "labels" && mapController.getLabelsTileUrl) {
                return mapController.getLabelsTileUrl(z, tx, ty);
            }
            if (mapController.getTileUrl) {
                return mapController.getTileUrl(z, tx, ty);
            }
        }
        return tileLayerRoot.baseUrl.replace("{z}", z).replace("{x}", tx).replace("{y}", ty);
    }

    Repeater {
        id: poolRepeater
        model: poolCount

        delegate: Loader {
            id: tileLoader
            property int colIndex: index % poolCols
            property int rowIndex: Math.floor(index / poolCols)
            
            property int tileX: viewLeftTile + colIndex
            property int tileY: viewTopTile + rowIndex
            property int maxTileX: tileLayerRoot.hasLocalTiles ? tileLayerRoot.localTileCols - 1 : Math.pow(2, tileLayerRoot.layerZoom) - 1
            property int maxTileY: tileLayerRoot.hasLocalTiles ? tileLayerRoot.localTileRows - 1 : Math.pow(2, tileLayerRoot.layerZoom) - 1
            
            property bool isValidTile: tileX >= 0 && tileX <= maxTileX && tileY >= 0 && tileY <= maxTileY
            property int tilePixelWidth: tileLayerRoot.hasLocalTiles && tileX === maxTileX ? tileLayerRoot.lastTileWidth : tileLayerRoot.tileSize
            property int tilePixelHeight: tileLayerRoot.hasLocalTiles && tileY === maxTileY ? tileLayerRoot.lastTileHeight : tileLayerRoot.tileSize
            property string tileSource: isValidTile ? tileLayerRoot.tileUrlFor(tileLayerRoot.layerZoom, tileX, tileY) : ""
            
            x: tileX * tileLayerRoot.tileSize
            y: tileY * tileLayerRoot.tileSize
            width: tilePixelWidth
            height: tilePixelHeight
            
            active: isValidTile && !tileLayerRoot.hideTiles && tileSource.length > 0
            
            sourceComponent: Image {
                source: tileLoader.tileSource
                asynchronous: true
                cache: true
                sourceSize.width: tileLoader.tilePixelWidth
                sourceSize.height: tileLoader.tilePixelHeight
                fillMode: Image.Stretch
                visible: status === Image.Ready
                
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
