import { Renew } from '@carbon/icons-react';
import {
  Header,
  HeaderGlobalAction,
  HeaderGlobalBar,
  HeaderName,
} from '@carbon/react';

const HeaderNav = ({ onNewChat }) => (
  <Header aria-label="IBM Power Sales Manual Assistant">
    <HeaderName href="/" prefix="IBM">
      Power Sales Manual Assistant
    </HeaderName>
    <HeaderGlobalBar>
      <HeaderGlobalAction
        aria-label="Start new conversation"
        tooltipAlignment="end"
        onClick={onNewChat}
      >
        <Renew size={20} />
      </HeaderGlobalAction>
    </HeaderGlobalBar>
  </Header>
);

export default HeaderNav;
