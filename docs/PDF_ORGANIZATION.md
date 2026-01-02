# PDF Organization Feature

## Overview

The PDF organization feature automatically renames uploaded PDF files based on extracted metadata after successful AI extraction. This makes it easier to identify and manage papers in the file system.

## Naming Convention

PDFs are renamed using the following format:

```
{author} - {year} - {title}.pdf
```

### Examples

**Single author:**
```
Magrini - 2020 - Real-time optimal quantum control of mechanical motion at room temperature.pdf
```

**Multiple authors:**
```
Smith et al - 2021 - Deep Learning for Computer Vision.pdf
```

**Missing year:**
```
Johnson - Unknown - Machine Learning Applications.pdf
```

## When Files Are Renamed

Files are automatically renamed when:

1. ✅ Metadata extraction completes successfully (`extraction_status = "completed"`)
2. ✅ Extraction confidence is ≥ 70% (`extraction_confidence >= 0.7`)
3. ✅ At least the title is available in the metadata

If any of these conditions are not met, the original filename is preserved.

## Implementation Details

### Filename Sanitization

Special characters that are invalid in filenames are automatically removed or replaced:

- **Removed:** `< > : " / \ | ? *` and control characters
- **Normalized:** Multiple spaces are collapsed to single spaces
- **Limited:** Each component has length limits to prevent filesystem issues:
  - Author: 50 characters
  - Year: 20 characters (usually just 4 digits)
  - Title: 100 characters

### Duplicate Handling

If a file with the target name already exists, a counter is automatically added:

```
Smith et al - 2021 - Deep Learning for Computer Vision (1).pdf
Smith et al - 2021 - Deep Learning for Computer Vision (2).pdf
```

### Author Name Extraction

The system handles different author formats:

1. **Structured format** (from APIs):
   ```python
   [{"given": "John", "family": "Smith"}, {...}]
   ```
   → Uses the family name of the first author

2. **String format** (from PDF text):
   ```python
   "John Smith, Jane Doe"
   ```
   → Uses the first name before the comma

3. **Multiple authors:**
   - Automatically appends "et al." when more than one author is detected

## Code Location

The feature is implemented in [`app/ai/tasks.py`](../app/ai/tasks.py):

- `sanitize_filename()`: Cleans text for use in filenames
- `generate_organized_filename()`: Creates the new filename from metadata
- `organize_pdf_file()`: Performs the actual file renaming
- `update_paper_extraction_results()`: Calls organization after successful extraction

## Testing

Run the test suite to verify filename generation:

```bash
python minimals/test_pdf_organization.py
```

Test cases cover:
- Single and multiple authors
- Different metadata formats
- Special characters in titles
- Missing fields
- Edge cases

## Database Updates

When a file is successfully renamed:

1. The new file path is saved to the database (`paper.file_path`)
2. The change is committed along with the metadata updates
3. All subsequent operations use the new file path

## Error Handling

If renaming fails for any reason:

- The original filename is preserved
- An error is logged but does not fail the extraction task
- The metadata is still saved to the database
- The system continues normal operation

## Configuration

No additional configuration is required. The feature uses:

- The existing upload directory from `config.py` (`upload_dir`)
- Confidence threshold: 0.7 (can be adjusted in `update_paper_extraction_results`)

## Future Enhancements

Potential improvements:

- [ ] Configurable naming templates via settings
- [ ] Option to organize into subdirectories by year or author
- [ ] Bulk rename existing PDFs through admin interface
- [ ] Custom filename patterns per collection
- [ ] Preserve original filename in metadata

## Troubleshooting

**Q: My PDF wasn't renamed. Why?**

A: Check the logs. The most common reasons are:
- Extraction confidence < 70%
- Missing title in metadata
- Extraction failed or incomplete

**Q: Can I change the naming format?**

A: Yes, modify the `generate_organized_filename()` function in `app/ai/tasks.py`. Update the filename construction around line 98.

**Q: What if I want to rename existing PDFs?**

A: Currently, the feature only renames PDFs during new extractions. To rename existing files, you would need to trigger a re-extraction or create a migration script.

**Q: Are the original filenames preserved anywhere?**

A: Not currently. The database only stores the current file path. If you need to preserve original filenames, consider adding an `original_filename` field to the database schema.
