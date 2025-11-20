# Documentation Consolidation Plan

## Current Problem
- 33+ documentation files scattered across the project
- Duplication and conflicting information
- Hard to find what you need
- Outdated guides mixed with current ones

## Solution: Single Documentation Structure

```
README.md              ← Main documentation (HOW TO RUN THE SYSTEM)
docs/
  ├── API.md          ← All API endpoints
  ├── DEPLOYMENT.md   ← Production deployment only
  └── ARCHIVE/        ← Old docs moved here
```

---

## Files to DELETE (Duplicates/Outdated)

### Deployment Files (DUPLICATE)
- [ ] `DEPLOY_COMMANDS.txt`
- [ ] `DEPLOYMENT_STEPS.txt`
- [ ] `FINAL_DEPLOYMENT_STEPS.txt`
- [ ] `STAGING_DEPLOY_COMMANDS.txt`
- [ ] `DEPLOY_ENSEMBLE_SCRIPT.md`

**Reason**: All covered in new README.md

### Architecture Files (DUPLICATE)
- [ ] `ARCHITECTURE.md`
- [ ] `API_ARCHITECTURE_ANALYSIS.md`
- [ ] `COMPREHENSIVE_ARCHITECTURE_OVERVIEW.md`
- [ ] `mapviewer_layout_analysis.md`
- [ ] `layout_diagram.txt`

**Reason**: Architecture section in README.md is sufficient

### Quick Reference Files (DUPLICATE)
- [ ] `quick_reference.md`
- [ ] `QUICK_REFERENCE.txt`
- [ ] `API_QUICK_REFERENCE.txt`

**Reason**: API section in README.md covers this

### Ensemble-Specific Files (OUTDATED/TOO SPECIFIC)
- [ ] `ENSEMBLE_DATA_GUIDE.md`
- [ ] `ENSEMBLE_DOWNLOAD_STATUS.md`
- [ ] `ENSEMBLE_MANUAL_DOWNLOAD.md`
- [ ] `REQUEST_ENSEMBLE_ACCESS_EMAIL.md`

**Reason**: Implementation-specific, belongs in /docs/ARCHIVE/

### Migration/Implementation Guides (OUTDATED)
- [ ] `STAC_EAOPI_MIGRATION_ROADMAP.md`
- [ ] `EOAPI_IMPLEMENTATION_GUIDE.md`
- [ ] `EOAPI_TESTING_GUIDE.md`
- [ ] `GeoSFM_CLIENT_SIDE_GUIDE.md`

**Reason**: Implementation done, no longer needed

### Frontend Refactoring Docs (OUTDATED)
- [ ] `frontend/REFACTORING_GUIDE.md`
- [ ] `frontend/CSS_REFACTORING_SUMMARY.md`
- [ ] `frontend/MODULAR_STRUCTURE_SUMMARY.md`
- [ ] `frontend/README.md` (replace with simpler version)

**Reason**: Refactoring in progress, will be obsolete

### Misc/Platform-Specific
- [ ] `replit.md` (not using Replit)
- [ ] `MAPSERVER_SYMBOLOGY_REFERENCE.md` (too technical, move to ARCHIVE)

---

## Files to KEEP

### Essential Files
- [x] `README.md` - NEW main documentation
- [x] `ADMIN_CREDENTIALS.md` - Keep but merge into README
- [x] `.env` files - Configuration
- [x] `requirements.txt` files - Dependencies

---

## Run the Cleanup

```bash
# 1. Create docs archive folder
mkdir -p docs/ARCHIVE

# 2. Move old docs to archive
mv ARCHITECTURE.md docs/ARCHIVE/
mv API_ARCHITECTURE_ANALYSIS.md docs/ARCHIVE/
mv COMPREHENSIVE_ARCHITECTURE_OVERVIEW.md docs/ARCHIVE/
mv mapviewer_layout_analysis.md docs/ARCHIVE/
mv layout_diagram.txt docs/ARCHIVE/

mv DEPLOY_COMMANDS.txt docs/ARCHIVE/
mv DEPLOYMENT_STEPS.txt docs/ARCHIVE/
mv FINAL_DEPLOYMENT_STEPS.txt docs/ARCHIVE/
mv STAGING_DEPLOY_COMMANDS.txt docs/ARCHIVE/
mv DEPLOY_ENSEMBLE_SCRIPT.md docs/ARCHIVE/

mv quick_reference.md docs/ARCHIVE/
mv QUICK_REFERENCE.txt docs/ARCHIVE/
mv API_QUICK_REFERENCE.txt docs/ARCHIVE/

mv ENSEMBLE_DATA_GUIDE.md docs/ARCHIVE/
mv ENSEMBLE_DOWNLOAD_STATUS.md docs/ARCHIVE/
mv ENSEMBLE_MANUAL_DOWNLOAD.md docs/ARCHIVE/
mv REQUEST_ENSEMBLE_ACCESS_EMAIL.md docs/ARCHIVE/

mv STAC_EAOPI_MIGRATION_ROADMAP.md docs/ARCHIVE/
mv EOAPI_IMPLEMENTATION_GUIDE.md docs/ARCHIVE/
mv EOAPI_TESTING_GUIDE.md docs/ARCHIVE/
mv GeoSFM_CLIENT_SIDE_GUIDE.md docs/ARCHIVE/

mv replit.md docs/ARCHIVE/
mv MAPSERVER_SYMBOLOGY_REFERENCE.md docs/ARCHIVE/

mv frontend/REFACTORING_GUIDE.md docs/ARCHIVE/
mv frontend/CSS_REFACTORING_SUMMARY.md docs/ARCHIVE/
mv frontend/MODULAR_STRUCTURE_SUMMARY.md docs/ARCHIVE/

# 3. Merge credentials into README (then delete)
cat ADMIN_CREDENTIALS.md >> README.md
rm ADMIN_CREDENTIALS.md

# 4. Create simple frontend README
echo "# Frontend

See main README.md in project root for all documentation.

## Quick Start
\`\`\`bash
npm install
npm run dev
\`\`\`
" > frontend/README.md

echo "✅ Documentation cleanup complete!"
echo "📄 Main docs: README.md"
echo "📦 Old docs: docs/ARCHIVE/"
```

---

## Result

**Before**: 33 documentation files (200KB+)
**After**: 1 main README.md (20KB)

All essential information in one place. Old docs archived for reference if needed.
