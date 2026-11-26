import { useEffect, useState } from 'react';
import { BusEventType, ChatCustomElement, CornersType, UserType } from '@carbon/ai-chat';
import './App.scss';
import { Column, Content, Grid, Theme } from '@carbon/react';
import { customSendMessage } from './customSendMessage.jsx';
import HeaderNav from './HeaderNav.jsx';
import { renderUserDefinedResponse } from './renderUserDefinedResponse.jsx';
import SourcesPage from './SourcesPage.jsx';

const WELCOME_MESSAGE =
  'Hi, I am the IBM Power Sales Manual Assistant. Ask me about IBM Power servers - features, activations, specifications and lifecycle dates. Answers come from the IBM Sales Manuals, with a link to the source page.';

const EXAMPLE_QUESTIONS = [
  'What are the key features of the IBM Power E1180?',
  'When is the IBM Power E980 withdrawn from marketing?',
  'What processor activation features are available for the IBM Power S1022?',
];

const BOT_PROFILE = {
  id: 'assistant',
  nickname: 'Sales Manual Assistant',
  user_type: UserType.BOT,
};

const layout = { corners: CornersType.SQUARE, hasContentMaxWidth: false };
const header = { title: 'Ask about IBM Power servers', hideMinimizeButton: true };
const messaging = { customSendMessage };

function onAfterRender(instance) {
  instance.on({ type: BusEventType.FEEDBACK, handler: () => {} });
  instance.messaging.addMessage({
    output: {
      generic: [
        { response_type: 'text', text: WELCOME_MESSAGE },
        {
          response_type: 'option',
          title: 'Try one of these:',
          options: EXAMPLE_QUESTIONS.map((q) => ({
            label: q,
            value: { input: { text: q } },
          })),
        },
      ],
    },
    message_options: { response_user_profile: BOT_PROFILE },
  });
}

const currentView = () => (window.location.hash === '#/sources' ? 'sources' : 'chat');

function onNewChat() {
  window.location.hash = '#/';
  window.location.reload();
}

function App() {
  const [view, setView] = useState(currentView);

  useEffect(() => {
    const onHashChange = () => setView(currentView());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  return (
    <Theme theme="white">
      <Content id="main-content">
        <Grid fullWidth className="chat-page-grid">
          <Column sm={4} md={8} lg={16}>
            <Theme theme="g90">
              <HeaderNav view={view} onNewChat={onNewChat} />
            </Theme>
          </Column>
          {view === 'sources' && (
            <Column sm={4} md={8} lg={16}>
              <SourcesPage />
            </Column>
          )}
          {/* Chat stays mounted while on Sources so the conversation is kept. */}
          <Column sm={4} md={8} lg={16} hidden={view !== 'chat'}>
            <div className="chat-container">
              <ChatCustomElement
                className="fullScreen"
                messaging={messaging}
                header={header}
                layout={layout}
                openChatByDefault={true}
                onAfterRender={onAfterRender}
                renderUserDefinedResponse={renderUserDefinedResponse}
              />
            </div>
          </Column>
        </Grid>
      </Content>
    </Theme>
  );
}

export default App;
