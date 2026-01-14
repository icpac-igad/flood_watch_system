import { connect } from "react-redux";

import Component from "./component";

import { getChooseAnalysisProps } from "./selectors";

export default connect(getChooseAnalysisProps)(Component);
