import weather from "./weather";
import satellite from "./satellite";
import flashFlood from "./flash-flood";

const allDatasets = [
  ...weather.datasets,
  ...satellite.datasets,
  ...flashFlood.datasets,
];

export const layersUpdateProviders = [
  ...weather.updates,
  ...satellite.updates,
  ...flashFlood.updates,
];

export default allDatasets;
