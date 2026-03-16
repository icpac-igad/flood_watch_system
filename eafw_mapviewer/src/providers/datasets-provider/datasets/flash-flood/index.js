import ffpi from "./ffpi";
import dffpi from "./dffpi";

const datasets = [...ffpi.datasets, ...dffpi.datasets];
const updates = [...ffpi.updates, ...dffpi.updates];

export default { datasets, updates };
