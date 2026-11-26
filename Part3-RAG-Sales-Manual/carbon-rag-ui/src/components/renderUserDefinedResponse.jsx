import {
  ClarificationBlock,
  FeaturesBlock,
  LifecycleTableBlock,
  MetaBlock,
  SourcesBlock,
} from './ChatBlocks.jsx';

function renderUserDefinedResponse(state, instance) {
  const data = state.messageItem?.user_defined;
  switch (data?.user_defined_type) {
    case 'clarification':
      return <ClarificationBlock data={data} instance={instance} />;
    case 'features':
      return <FeaturesBlock data={data} />;
    case 'lifecycle_table':
      return <LifecycleTableBlock data={data} />;
    case 'sources':
      return <SourcesBlock data={data} />;
    case 'meta':
      return <MetaBlock data={data} />;
    default:
      return undefined;
  }
}

export { renderUserDefinedResponse };
