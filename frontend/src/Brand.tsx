export function Wordmark() {
  return <svg className="brand-wordmark" width="128" height="22" viewBox="0 0 207 44" role="img" aria-label="LedgerFlow"><use href="/icons/wordmark.svg#wordmark" width="207" height="44" /></svg>;
}

/** The LedgerFlow mark: the cream receipt with a check (same drawing as the Mac intro). */
export function BrandMark({ size = 32 }: { size?: number }) {
  return <svg width={size * 110 / 124} height={size} viewBox="0 0 110 124" aria-hidden="true" className="ledger-mark">
    <path fill="#eaf2d8" stroke="#245843" strokeWidth="3" strokeLinejoin="round" d="M18 6h53l21 21v85l-12-8-12 8-12-8-12 8-12-8-14 8z"/>
    <path fill="#a9c395" d="M71 6v21h21z"/>
    <path fill="none" stroke="#245843" strokeLinecap="round" strokeWidth="3" d="M31 26h23m-23 16h43M31 55h43M31 68h43m-18 18 7 7 13-15"/>
  </svg>;
}

/** The selection device used across the product: a rectangle with a square fill handle. */
export function SelectionFrame({ className = "" }: { className?: string }) {
  return <span className={`selection-frame ${className}`} aria-hidden="true"><i /></span>;
}
