import { Renew } from '@carbon/icons-react';
import {
  Header,
  HeaderGlobalAction,
  HeaderGlobalBar,
  HeaderMenuItem,
  HeaderName,
  HeaderNavigation,
} from '@carbon/react';

const HeaderNav = ({ view, onNewChat }) => (
  <Header aria-label="IBM Power Sales Manual Assistant">
    <HeaderName href="#/" prefix="IBM">
      Power Sales Manual Assistant
    </HeaderName>
    <HeaderNavigation aria-label="Sections">
      <HeaderMenuItem href="#/" isCurrentPage={view === 'chat'}>
        Chat
      </HeaderMenuItem>
      <HeaderMenuItem href="#/sources" isCurrentPage={view === 'sources'}>
        Sources
      </HeaderMenuItem>
    </HeaderNavigation>
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
