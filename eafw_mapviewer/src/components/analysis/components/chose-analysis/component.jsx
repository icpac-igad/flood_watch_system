import React, { PureComponent } from "react";

import "./styles.scss";

class ChoseAnalysis extends PureComponent {

  renderLayerOption = () => {
    // const { boundaries, activeBoundary, selectBoundaries, setMenuSettings } =
    //   this.props;
    // const selectedBoundaries = activeBoundary || (boundaries && boundaries[0]);

    return (
      <div className="layer-menu">
       
        {/* <Dropdown
          className="boundary-selector analysis-boundary-menu"
          options={boundaries}
          value={selectedBoundaries && selectedBoundaries.value}
          onChange={selectBoundaries}
          native
        /> */}
      </div>
    );
  };

  render() {
    return (
      <div className="c-chose-analysis">
        <div className="analysis-placeholder">
          <p>Analysis tools coming soon...</p>
        </div>
      </div>
    );
  }
}

export default ChoseAnalysis;
