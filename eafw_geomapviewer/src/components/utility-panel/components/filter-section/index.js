import { connect } from 'react-redux';
import Component from './component';
import { setSelectedFilterType } from '@/components/utility-panel/actions';
import { selectFilterTypes } from '@/providers/config-provider/selectors';

const mapStateToProps = (state) => ({
  filterTypes: selectFilterTypes(state),
});

export default connect(mapStateToProps, { setSelectedFilterType })(Component);
