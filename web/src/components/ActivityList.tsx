import { ArrowRight, Minus, Pencil, Plus } from 'lucide-react';
import type { Activity } from '../lib/types';
import { activityLabel, shortDate } from '../lib/format';
import { Money } from './Money';
import { EmptyState } from './EmptyState';

interface Props {
  items: Activity[];
  onEdit?: (item: Activity) => void;
  emptyTitle: string;
  emptyHint?: string;
}

/**
 * The one place movements and transfers are rendered. Rows are read left to
 * right as a sentence — what it was, where it happened, when — with the amount
 * pinned right so a column of figures can be scanned vertically.
 */
export function ActivityList({ items, onEdit, emptyTitle, emptyHint }: Props) {
  if (items.length === 0) {
    return <EmptyState title={emptyTitle} hint={emptyHint} />;
  }

  return (
    <ul className="divide-y divide-line">
      {items.map((item) => (
        <li
          key={item.id}
          className="group flex items-center gap-3 px-5 py-3 hover:bg-surface-hover
            transition-colors"
        >
          <Glyph kind={item.kind} />

          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-medium truncate" data-selectable>
              {activityLabel(item)}
            </p>
            <p className="flex items-center gap-1.5 text-[11px] text-text-subtle mt-0.5">
              <span className="truncate">{item.account_name}</span>
              {item.to_account_name && (
                <>
                  <ArrowRight size={10} className="shrink-0" />
                  <span className="truncate">{item.to_account_name}</span>
                </>
              )}
              <span aria-hidden>·</span>
              <span className="shrink-0">{shortDate(item.date)}</span>
              {item.record === 'movement' && item.pending === 1 && (
                <span
                  title="Se incluirá en la próxima conciliación"
                  className="shrink-0 size-1.5 rounded-full bg-caution"
                />
              )}
            </p>
          </div>

          <Money
            amount={signedAmount(item)}
            tone={item.record === 'transfer' ? 'neutral' : 'auto'}
            signed={item.record !== 'transfer'}
            className="text-[13px] font-medium shrink-0"
          />

          {onEdit && (
            <button
              type="button"
              onClick={() => onEdit(item)}
              aria-label={`Editar ${activityLabel(item)}`}
              title="Editar"
              className="shrink-0 grid place-items-center size-7 rounded-[6px]
                text-text-subtle hover:text-text hover:bg-surface-hover transition-colors"
            >
              <Pencil size={13} />
            </button>
          )}
        </li>
      ))}
    </ul>
  );
}

function signedAmount(item: Activity): number {
  return item.kind === 'expense' ? -item.amount : item.amount;
}

function Glyph({ kind }: { kind: Activity['kind'] }) {
  const styles = {
    income: 'bg-positive/12 text-positive',
    expense: 'bg-negative/12 text-negative',
    transfer: 'bg-surface-hover text-text-subtle',
  }[kind];

  const icon = {
    income: <Plus size={13} />,
    expense: <Minus size={13} />,
    transfer: <ArrowRight size={13} />,
  }[kind];

  return (
    <span className={`grid place-items-center size-7 rounded-full shrink-0 ${styles}`}>
      {icon}
    </span>
  );
}
