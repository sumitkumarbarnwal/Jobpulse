import { useRef } from 'react';

interface JobFiltersProps {
  search: string;
  remote: '' | 'true' | 'false';
  location: string;
  onChange: (filters: { search: string; remote: '' | 'true' | 'false'; location: string }) => void;
}

export function JobFilters({ search, remote, location, onChange }: JobFiltersProps) {
  const searchRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearchChange = (value: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onChange({ search: value, remote, location });
    }, 350);
  };

  return (
    <div className="jobs-filter-row">
      {/* Search */}
      <div className="jobs-search-wrap">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          ref={searchRef}
          id="job-search"
          type="text"
          className="jobs-search-input"
          placeholder="Search jobs..."
          defaultValue={search}
          onChange={(e) => handleSearchChange(e.target.value)}
        />
      </div>

      {/* Remote filter */}
      <div className="jobs-filter-select-icon">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
        </svg>
        <select
          id="job-filter-remote"
          className="jobs-filter-select"
          value={remote}
          onChange={(e) => onChange({ search, remote: e.target.value as '' | 'true' | 'false', location })}
        >
          <option value="">Remote</option>
          <option value="true">Remote only</option>
          <option value="false">On-site only</option>
        </select>
      </div>

      {/* Location filter */}
      <div className="jobs-filter-select-icon">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
        </svg>
        <select
          id="job-filter-location"
          className="jobs-filter-select"
          value={location}
          onChange={(e) => onChange({ search, remote, location: e.target.value })}
        >
          <option value="">Location</option>
          <option value="remote">Remote</option>
          <option value="us">United States</option>
          <option value="uk">United Kingdom</option>
          <option value="eu">Europe</option>
          <option value="india">India</option>
          <option value="global">Global</option>
        </select>
      </div>

      {/* Clear */}
      {(search || remote || location) && (
        <button
          id="job-filter-clear"
          className="btn btn-secondary"
          style={{ padding: '5px 10px', fontSize: '0.78rem', flexShrink: 0 }}
          onClick={() => {
            onChange({ search: '', remote: '', location: '' });
            if (searchRef.current) searchRef.current.value = '';
          }}
        >
          Clear
        </button>
      )}
    </div>
  );
}
