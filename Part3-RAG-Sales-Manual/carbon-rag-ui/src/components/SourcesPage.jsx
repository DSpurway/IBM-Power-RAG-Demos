import { useEffect, useState } from 'react';
import {
  DataTable,
  InlineNotification,
  Link,
  SkeletonText,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  TableToolbar,
  TableToolbarContent,
  TableToolbarSearch,
  Tag,
} from '@carbon/react';
import { Launch } from '@carbon/icons-react';

const HEADERS = [
  { key: 'name', header: 'Server' },
  { key: 'mtms', header: 'Machine type-model' },
  { key: 'family', header: 'Family' },
  { key: 'published', header: 'Published' },
  { key: 'chunks', header: 'Indexed chunks' },
  { key: 'url', header: 'IBM Sales Manual', isSortable: false },
];

const toRow = (s) => ({
  id: s.family,
  name: s.name,
  mtms: s.mtms.join(', '),
  family: s.family,
  published: s.published || '-',
  chunks: s.chunks,
  url: s.url,
});

function renderCell(cell) {
  const { value, info } = cell;
  if (info.header === 'url') {
    return (
      <Link href={value} target="_blank" rel="noopener noreferrer" renderIcon={Launch}>
        Open
      </Link>
    );
  }
  if (info.header === 'chunks') {
    if (value === null || value === undefined) return '-';
    return value === 0 ? <Tag type="red" size="sm">Not indexed</Tag> : value;
  }
  return value;
}

function SourcesTable({ set }) {
  return (
    <DataTable rows={set.sources.map(toRow)} headers={HEADERS} isSortable>
      {({ rows, headers, getHeaderProps, getRowProps, getTableProps, onInputChange }) => (
        <TableContainer title={set.title} description={set.description}>
          <TableToolbar>
            <TableToolbarContent>
              <TableToolbarSearch
                persistent
                placeholder="Filter by server, type-model or family"
                onChange={onInputChange}
              />
            </TableToolbarContent>
          </TableToolbar>
          <Table {...getTableProps()}>
            <TableHead>
              <TableRow>
                {headers.map((header) => {
                  const { key, ...props } = getHeaderProps({ header });
                  return (
                    <TableHeader key={key} {...props}>
                      {header.header}
                    </TableHeader>
                  );
                })}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => {
                const { key, ...props } = getRowProps({ row });
                return (
                  <TableRow key={key} {...props}>
                    {row.cells.map((cell) => (
                      <TableCell key={cell.id}>{renderCell(cell)}</TableCell>
                    ))}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </DataTable>
  );
}

/** Read-only list of the IBM documentation the assistant answers from. */
export default function SourcesPage() {
  const [sets, setSets] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/sources', { signal: controller.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => setSets(data.sets || []))
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message);
      });
    return () => controller.abort();
  }, []);

  if (error) {
    return (
      <InlineNotification
        kind="error"
        title="Could not load the source list."
        subtitle={error}
        hideCloseButton
      />
    );
  }
  if (!sets) return <SkeletonText paragraph lineCount={6} />;
  return (
    <>
      <p className="sources-intro">
        The assistant answers only from these IBM pages. Each links to the original IBM Sales Manual.
      </p>
      {sets.map((set) => (
        <SourcesTable key={set.id} set={set} />
      ))}
    </>
  );
}
