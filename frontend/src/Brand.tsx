export function Wordmark() {
  return <svg className="brand-wordmark" width="128" height="22" viewBox="0 0 207 32" role="img" aria-label="LedgerFlow"><use href="/icons/wordmark.svg#wordmark" width="207" height="32" /></svg>;
}

/** The LF monogram as a selected cell: the forest tile is the cell, the mint square is the spreadsheet fill handle. */
export function BrandMark({ size = 32 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" className="ledger-mark">
    <rect x="1" y="1" width="56" height="56" rx="12" fill="var(--mark-tile, #0B5A45)" />
    <g transform="translate(1.2 1.2) scale(.875)">
      <path d="M16 14H24V41H34V49H16Z" fill="var(--mark-l, #FFFFFF)" />
      <path d="M32 14H49V22H40V29H47V37H40V49H32Z" fill="var(--mark-f, #BFEBD3)" />
    </g>
    <rect x="47" y="47" width="15" height="15" rx="3" fill="var(--mark-handle, #8FE3B8)" stroke="var(--mark-ring, #FFFFFF)" strokeWidth="3" />
  </svg>;
}

/** The selection device used across the product: a rectangle with a square fill handle. */
export function SelectionFrame({ className = "" }: { className?: string }) {
  return <span className={`selection-frame ${className}`} aria-hidden="true"><i /></span>;
}
