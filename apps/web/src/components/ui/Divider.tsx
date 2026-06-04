/** The ONE divider (spec §10.4): 1px --hint@12%. No ad-hoc borders. */
export function Divider({ className = "" }: { className?: string }) {
    return <hr className={`border-0 border-t border-hairline ${className}`} />;
}
