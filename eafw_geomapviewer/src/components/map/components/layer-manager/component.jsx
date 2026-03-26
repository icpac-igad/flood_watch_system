import React, { PureComponent } from "react";
import PropTypes from "prop-types";
import { LayerManager, Layer } from "@wmo-raf/layer-manager/dist/components";
import { PluginMapboxGl } from "@wmo-raf/layer-manager";
import { connect } from "react-redux";
import { processLayers } from "@/utils/layer-utils";
import { selectParamInteractions } from "@/components/map/selectors";


class LayerManagerComponent extends PureComponent {
  static propTypes = {
    loading: PropTypes.bool,
    layers: PropTypes.array,
    basemap: PropTypes.object,
    setMapLoading: PropTypes.func,
    map: PropTypes.object,
    allDatasets: PropTypes.array,
    activeDatasets: PropTypes.array,
    setMapSettings: PropTypes.func,
  };

  state = {
    layerModels: {},
  };

  moveBoundaryLayersToTop = () => {
    const { map } = this.props;
    const { layerModels } = this.state;
    if (!map) return;

    Object.values(layerModels)
      .filter((entry) => entry?.isBoundary)
      .forEach((entry) => {
        const mapLayers = entry?.mapLayer?.layers || [];
        mapLayers.forEach((mapLayer) => {
          if (mapLayer?.id && map.getLayer(mapLayer.id)) {
            map.moveLayer(mapLayer.id);
          }
        });
      });
  };

  componentDidUpdate(prevProps, prevState) {
    const { layers } = this.props;

    for (let i = 0; i < layers.length; i++) {
      const layer = layers[i];
      if (this.state.layerModels[layer.id]) {
        this.setLayerFilter(layer.id, layer.layerFilterParams, layer);
      }
    }

    if (prevProps.layers !== layers || prevState.layerModels !== this.state.layerModels || prevProps.paramInteractions !== this.props.paramInteractions) {
      setTimeout(this.moveBoundaryLayersToTop, 0);
    }
  }

  setLayerFilter = (layerId, filterParams, layer) => {
    const { map } = this.props;

    const layerModelEntry = this.state.layerModels[layerId];
    const mapLayerModel = layerModelEntry?.mapLayer || layerModelEntry;
    const mapLayers = mapLayerModel?.layers || [];
    if (!map || !mapLayers.length || !filterParams) return;

    const layersWithFilters = mapLayers.filter((l) => l && l.filter);

    const { layerFilterParamsConfig } = layer;

    const filterKey =
      layerFilterParamsConfig &&
      layerFilterParamsConfig[0] &&
      layerFilterParamsConfig[0].key;

    for (let i = 0; i < layersWithFilters.length; i++) {
      const mapLayer = layersWithFilters[i];

      Object.keys(filterParams).forEach(() => {
        if (filterParams[filterKey]) {
          const literalVals = filterParams[filterKey].map((f) => f.value);

                    // filter: ["in", ["get", "severity"], ["literal", [5, 4, 3, 2]]],

          const lFilter = ["in", ["get", filterKey], ["literal", literalVals]];

          map.setFilter(mapLayer.id, lFilter);
        }
      });
    }
  };

  handleOnAdd = (layerModel) => {
    const { allDatasets, activeDatasets, setMapSettings, setMainMapSettings } =
      this.props;

    if (layerModel && layerModel.isMultiLayer && layerModel.isDefault) {
      const { dataset, linkedLayers, showAllMultiLayer } = layerModel;

      if (showAllMultiLayer && linkedLayers && !!linkedLayers.length) {
        const newActiveDatasets = activeDatasets.map((newDataset, i) => {
          if (newDataset.dataset === dataset) {
            const newActiveDataset = activeDatasets[i];
            return {
              ...newActiveDataset,
              layers: [...newActiveDataset.layers, ...linkedLayers],
            };
          }
          return newDataset;
        });

        setMapSettings({ datasets: newActiveDatasets, canBound: true });
      }
    }

    this.setState(
      (prevState) => ({
        layerModels: {
          ...prevState.layerModels,
          [layerModel.id]: {
            isBoundary: !!layerModel.isBoundary,
            mapLayer: layerModel.mapLayer,
          },
        },
      }),
      () => {
        // Keep admin/boundary overlays above subsequently added thematic layers.
        setTimeout(this.moveBoundaryLayersToTop, 0);
      }
    );
  };

  handleOnRemove = (layerModel) => {
    this.setState(
      (prevState) => {
        const nextLayerModels = { ...prevState.layerModels };
        delete nextLayerModels[layerModel.id];
        return { layerModels: nextLayerModels };
      },
      () => {
        setTimeout(this.moveBoundaryLayersToTop, 0);
      }
    );
  };

  render() {
    const { layers, basemap, map, mapSide, paramInteractions } = this.props;

    const processedLayers = processLayers(layers, paramInteractions, mapSide);

    const allLayers = processedLayers;

    return (
      <div className="map-container">
        <LayerManager map={map} plugin={PluginMapboxGl} providers={{}}>
          {allLayers.map((l) => {
            const config = l.config || l.layerConfig;
            return (
              <Layer
                key={l.id}
                {...l}
                {...config}
                onAfterAdd={this.handleOnAdd}
                onAfterRemove={this.handleOnRemove}
              />
            );
          })}
        </LayerManager>
      </div>
    );
  }
}

const mapStateToProps = (state) => ({
  paramInteractions: selectParamInteractions(state)
});

export default connect(mapStateToProps)(LayerManagerComponent);
