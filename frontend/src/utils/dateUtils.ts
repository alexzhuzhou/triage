/**
 * Formats a date string (YYYY-MM-DD) to a localized date string
 * without timezone conversion issues.
 *
 * @param dateString - Date string in YYYY-MM-DD format
 * @returns Formatted date string
 */
export function formatDateOnly(dateString: string): string {
  // Parse the date components directly to avoid timezone issues
  const [year, month, day] = dateString.split('-').map(Number);
  const date = new Date(year, month - 1, day); // month is 0-indexed
  return date.toLocaleDateString();
}

/**
 * Formats a datetime string to a localized date and time string.
 *
 * @param datetimeString - ISO datetime string
 * @returns Formatted datetime string
 */
export function formatDateTime(datetimeString: string): string {
  return new Date(datetimeString).toLocaleString();
}
