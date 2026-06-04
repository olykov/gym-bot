/** The ONE card style (spec §10.4): --bg surface, hairline + single shadow
 *  token, radius + padding tokens. No other card variants exist. */
import type { HTMLAttributes, ReactNode } from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
    children: ReactNode;
    /** Tighter padding for dense grids (still a token). */
    flush?: boolean;
}

export function Card({ children, flush = false, className = "", ...rest }: CardProps) {
    return (
        <div
            className={`rounded-lg border border-hairline bg-bg shadow-card ${
                flush ? "p-3" : "p-4"
            } ${className}`}
            {...rest}
        >
            {children}
        </div>
    );
}
