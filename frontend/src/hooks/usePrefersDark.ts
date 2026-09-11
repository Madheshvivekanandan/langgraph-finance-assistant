import { useMediaQuery } from './useMediaQuery'

/** True while the OS colour scheme is dark. Live — flips without a reload (D4). */
export function usePrefersDark(): boolean {
  return useMediaQuery('(prefers-color-scheme: dark)')
}
