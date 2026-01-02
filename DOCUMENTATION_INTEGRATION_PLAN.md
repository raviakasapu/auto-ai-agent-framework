# Documentation Systems Integration Plan

## Current State Analysis

### System 1: Main Documentation (`docs_source/source/`)
**Location:** `docs_source/source/`  
**Purpose:** Comprehensive framework documentation  
**Structure:** Part-based organization (Part 1-7, plus guides, tutorials, API)

**Content Structure:**
- `part1_orientation/` - Quickstart, conceptual model, overview
- `part2_runtime/` - Runtime building blocks (agents, memory, tools, planners, policies, etc.)
- `part3_solutions/` - Building solutions (configuration, deployment, flows, etc.)
- `part4_cookbook/` - Extensibility recipes
- `part5_operations/` - Operations (monitoring, security, troubleshooting)
- `part6_playbooks/` - Domain-specific playbooks
- `part7_reference/` - Reference materials
- `guides/` - Additional guides
- `tutorials/` - Step-by-step tutorials
- `api/` - API reference
- `powerbi/` - Power BI implementation docs

**Key Files:**
- `part3_solutions/configuration.md` - Basic YAML configuration guide (312 lines, less detailed)
- `part2_runtime/agents.md` - Agents & Manager stack
- `part2_runtime/memory.md` - Memory & message stores
- `part2_runtime/planners.md` - Planners & gateways
- `part2_runtime/policies.md` - Policies & presets
- `part2_runtime/tools.md` - Tools & decorators

---

### System 2: PyPI Package Documentation (`agent-framework-pypi/docs/`)
**Location:** `agent-framework-pypi/docs/`  
**Purpose:** Standalone package documentation (currently separate build)  
**Structure:** Guide-based organization

**Content Structure:**
- `guides/` - Focused configuration guides
  - `yaml-configuration.md` - **Detailed YAML config guide (501 lines)**
  - `agent-types.md` - Agent types guide (372 lines)
  - `memory-presets.md` - Memory presets guide (350 lines)
  - `policy-presets.md` - Policy presets guide
  - `tools.md` - Tools guide (425 lines)
  - `planners.md` - Planners guide
- `examples/` - Example implementations
- `api/` - API reference (core, components, policies)
- `getting-started.md`, `quickstart.md` - Getting started guides
- `testing.md`, `contributing.md` - Development docs

---

## Content Overlap Analysis

### Overlapping Topics

| Topic | Main Docs | PyPI Docs | Status |
|-------|-----------|-----------|--------|
| **YAML Configuration** | `part3_solutions/configuration.md` (312 lines, basic) | `guides/yaml-configuration.md` (501 lines, **detailed**) | ⚠️ PyPI version is more comprehensive |
| **Agents** | `part2_runtime/agents.md` (comprehensive) | `guides/agent-types.md` (372 lines, focused) | ⚠️ Different focus - main docs more comprehensive |
| **Memory** | `part2_runtime/memory.md` (comprehensive) | `guides/memory-presets.md` (350 lines, preset-focused) | ⚠️ Different focus - PyPI focuses on presets |
| **Policies** | `part2_runtime/policies.md` (comprehensive) | `guides/policy-presets.md` (preset-focused) | ⚠️ Different focus |
| **Planners** | `part2_runtime/planners.md` (comprehensive) | `guides/planners.md` (focused) | ⚠️ Different focus |
| **Tools** | `part2_runtime/tools.md` (comprehensive) | `guides/tools.md` (425 lines) | ⚠️ Need to compare depth |

### Unique Content

**Main Docs Only:**
- Part 1-7 comprehensive structure
- Tutorials
- Power BI implementation
- Operations & troubleshooting
- Domain playbooks
- Legacy guides

**PyPI Docs Only:**
- Focused preset guides (memory-presets, policy-presets)
- Package-specific examples
- Package getting started (may differ from main docs)

---

## Integration Strategy

### Goal
Create a **single, unified documentation system** using `docs_source/source/` as the primary location, with PyPI docs integrated as enhanced/supplementary content.

### Principle
- **Primary System:** `docs_source/source/` (main comprehensive docs)
- **Integration Method:** Enhance existing docs with detailed PyPI content where appropriate
- **Result:** One documentation system, one build process, one source of truth

---

## Detailed Integration Plan

### Phase 1: Content Comparison & Gap Analysis

#### Task 1.1: Compare YAML Configuration Guides
- [ ] **Compare:** `docs_source/source/part3_solutions/configuration.md` vs `agent-framework-pypi/docs/guides/yaml-configuration.md`
- [ ] **Action:** 
  - Identify unique sections in PyPI version
  - Check if PyPI version uses newer schema (`apiVersion`, `kind`, `metadata` vs old `name`, `type`)
  - Determine if PyPI version should replace or supplement main docs version
- [ ] **Decision Point:** Should we replace the main docs version or merge both?

#### Task 1.2: Compare Agent Documentation
- [ ] **Compare:** `part2_runtime/agents.md` vs `guides/agent-types.md`
- [ ] **Action:**
  - Check if PyPI guide has unique examples or patterns
  - Identify if PyPI guide is more YAML-focused vs code-focused
- [ ] **Decision:** Merge unique content or keep separate with cross-references?

#### Task 1.3: Compare Memory Documentation
- [ ] **Compare:** `part2_runtime/memory.md` vs `guides/memory-presets.md`
- [ ] **Action:**
  - PyPI guide focuses on presets - should this be integrated into main memory.md?
  - Check if preset documentation is missing or incomplete in main docs
- [ ] **Decision:** Add preset section to main docs or keep as separate guide?

#### Task 1.4: Compare Policy Documentation
- [ ] **Compare:** `part2_runtime/policies.md` vs `guides/policy-presets.md`
- [ ] **Action:** Similar to memory - check preset coverage
- [ ] **Decision:** Integrate preset content or cross-reference?

#### Task 1.5: Compare Tools Documentation
- [ ] **Compare:** `part2_runtime/tools.md` vs `guides/tools.md`
- [ ] **Action:** Check depth and uniqueness of each
- [ ] **Decision:** Merge or supplement?

#### Task 1.6: Compare Planners Documentation
- [ ] **Compare:** `part2_runtime/planners.md` vs `guides/planners.md`
- [ ] **Action:** Check for unique examples or configurations
- [ ] **Decision:** Merge or supplement?

---

### Phase 2: Content Integration

#### Task 2.1: YAML Configuration Integration (HIGH PRIORITY)
**Current State:**
- Main docs: Basic configuration guide (312 lines)
- PyPI docs: Comprehensive guide (501 lines) with:
  - Complete schema reference
  - All top-level fields (`apiVersion`, `kind`, `metadata`)
  - Detailed resources section (inference_gateways, tools, subscribers)
  - Detailed spec section (policies with presets, planner configs, memory presets)
  - Complete examples
  - Validation section

**Integration Options:**

**Option A: Replace (Recommended)**
- Replace `docs_source/source/part3_solutions/configuration.md` with PyPI version
- **Pros:** More complete, uses latest schema, better examples
- **Cons:** Need to verify schema matches current implementation
- **Action:**
  1. Review PyPI yaml-configuration.md for accuracy
  2. Verify schema matches actual implementation
  3. Replace main docs file
  4. Update any references/cross-links

**Option B: Merge**
- Keep both structures, merge unique content
- **Pros:** Preserves existing organization
- **Cons:** More complex, potential duplication
- **Action:**
  1. Extract unique sections from PyPI version
  2. Integrate into main docs structure
  3. Remove duplicates

**Recommendation:** **Option A (Replace)** - PyPI version is more comprehensive and appears to be the authoritative reference.

#### Task 2.2: Preset Documentation Integration
**Current State:**
- PyPI has focused guides: `memory-presets.md`, `policy-presets.md`
- Main docs cover these topics but may not have dedicated preset sections

**Integration Options:**

**Option A: Add Preset Sections to Main Docs**
- Add "Memory Presets" section to `part2_runtime/memory.md`
- Add "Policy Presets" section to `part2_runtime/policies.md`
- Extract content from PyPI guides
- **Pros:** Keeps related content together
- **Cons:** Makes files longer

**Option B: Create New Preset Guide in Main Docs**
- Create `part2_runtime/memory-presets.md` and `part2_runtime/policy-presets.md`
- Copy/enhance PyPI content
- Update index.rst to include them
- **Pros:** Focused guides, easier to find
- **Cons:** More files to maintain

**Recommendation:** **Option B** - Presets are important enough to warrant focused guides, and they complement the comprehensive guides.

#### Task 2.3: Agent Types Integration
**Current State:**
- Main docs: Comprehensive `part2_runtime/agents.md`
- PyPI docs: Focused `guides/agent-types.md` (372 lines)

**Action:**
- Compare content depth
- If PyPI has unique examples/patterns, extract and add to main docs
- Consider if PyPI guide should become a focused "Agent Types Quick Reference"

#### Task 2.4: Tools & Planners Integration
**Action:**
- Compare both versions
- Extract unique examples, configurations, or patterns from PyPI guides
- Integrate into main docs
- Or create focused quick-reference guides if PyPI versions are more concise

---

### Phase 3: Structure & Navigation Updates

#### Task 3.1: Update Main Docs Index
- [ ] Review `docs_source/source/index.rst`
- [ ] Add new guides if created (e.g., preset guides)
- [ ] Ensure logical organization

#### Task 3.2: Update Part 2 Index (Runtime Building Blocks)
- [ ] Review `docs_source/source/part2_runtime/index.rst`
- [ ] Add new preset guides if created
- [ ] Ensure proper ordering

#### Task 3.3: Update Part 3 Index (Building Solutions)
- [ ] Review `docs_source/source/part3_solutions/index.rst`
- [ ] Ensure configuration.md is properly referenced
- [ ] Add cross-references to preset guides if needed

#### Task 3.4: Cross-Reference Updates
- [ ] Find all references to configuration/agents/memory/policies/tools/planners
- [ ] Update links if files are moved/renamed
- [ ] Add cross-references between comprehensive guides and focused guides

---

### Phase 4: PyPI Docs Consolidation

#### Task 4.1: Update PyPI Docs Index
**Options:**

**Option A: Redirect to Main Docs (Recommended)**
- Update `agent-framework-pypi/docs/index.rst` to point to main docs
- Add note: "For comprehensive documentation, see [main docs URL]"
- Keep only package-specific content (installation, package structure)
- **Pros:** Single source of truth
- **Cons:** Requires external link

**Option B: Keep PyPI Docs as Standalone**
- Keep separate but ensure content is synchronized
- **Pros:** Package has its own docs
- **Cons:** Maintenance burden, potential divergence

**Option C: Make PyPI Docs Symlink/Copy from Main**
- Use build process to copy/symlink from main docs
- **Pros:** Single source, package has docs
- **Cons:** More complex build setup

**Recommendation:** **Option A** for now, with path to Option C if needed.

#### Task 4.2: Package-Specific Content
- Identify content that's truly package-specific (e.g., installation from PyPI)
- Keep only package-specific content in PyPI docs
- Move general content to main docs

---

### Phase 5: Build Process Unification

#### Task 5.1: Verify Build Configuration
- [ ] Check `docs_source/source/conf.py`
- [ ] Ensure it can handle all integrated content
- [ ] Verify markdown processing (myst_parser)

#### Task 5.2: Test Build
- [ ] Build main docs after integration
- [ ] Verify all links work
- [ ] Check formatting
- [ ] Verify examples render correctly

#### Task 5.3: Update Build Documentation
- [ ] Update any build instructions
- [ ] Document that PyPI docs are now integrated into main docs

---

### Phase 6: Verification & Cleanup

#### Task 6.1: Content Verification
- [ ] Verify all PyPI guide content is integrated
- [ ] Check for duplicate content
- [ ] Verify examples are accurate
- [ ] Check code blocks render correctly

#### Task 6.2: Link Verification
- [ ] Check all internal links
- [ ] Verify cross-references
- [ ] Check external links

#### Task 6.3: Cleanup
- [ ] Remove duplicate content
- [ ] Archive or remove obsolete PyPI docs (if redirecting)
- [ ] Update any scripts that reference PyPI docs location

---

## Decision Matrix

### Critical Decisions Needed

1. **YAML Configuration: Replace or Merge?**
   - **Recommendation:** Replace with PyPI version (more comprehensive)
   - **Risk:** Need to verify schema accuracy
   - **Action:** Test with actual YAML files

2. **Preset Guides: Integrate or Separate?**
   - **Recommendation:** Create separate preset guides in main docs
   - **Rationale:** Presets are important, warrant focused guides
   - **Location:** `part2_runtime/memory-presets.md`, `part2_runtime/policy-presets.md`

3. **PyPI Docs: Redirect or Keep?**
   - **Recommendation:** Redirect to main docs, keep only package-specific content
   - **Long-term:** Consider build-time integration (Option C)

4. **Agent/Tools/Planners: Merge or Supplement?**
   - **Recommendation:** Compare first, then decide based on content uniqueness
   - **If unique:** Extract and integrate
   - **If redundant:** Use main docs version

---

## Implementation Checklist

### Pre-Integration
- [ ] Review PyPI yaml-configuration.md for accuracy against current implementation
- [ ] Compare all overlapping guides side-by-side
- [ ] Identify unique content in each
- [ ] Make decisions on each integration point

### Integration
- [ ] Replace/merge YAML configuration guide
- [ ] Create/update preset guides in main docs
- [ ] Integrate unique content from PyPI guides
- [ ] Update index files
- [ ] Update cross-references

### Post-Integration
- [ ] Build and test documentation
- [ ] Verify all links
- [ ] Update PyPI docs to redirect/reference main docs
- [ ] Document the integration
- [ ] Clean up duplicate files

---

## Success Criteria

✅ **Single Source of Truth:** All documentation in `docs_source/source/`  
✅ **No Duplication:** No duplicate content between systems  
✅ **Comprehensive:** All valuable content from both systems integrated  
✅ **Well Organized:** Logical structure with clear navigation  
✅ **Buildable:** Single build process produces complete documentation  
✅ **Maintainable:** Clear ownership and update process  

---

## Notes & Considerations

1. **Schema Verification:** PyPI yaml-configuration.md uses `apiVersion: agent.framework/v2`, `kind: Agent|ManagerAgent`, `metadata:` structure. Need to verify this matches actual implementation.

2. **Preset Focus:** PyPI guides focus heavily on presets (`$preset: simple`, etc.). Main docs may cover this but PyPI guides are more focused. Consider this a strength to integrate.

3. **Examples:** PyPI docs may have more/better examples. Preserve these.

4. **Build Dependencies:** Ensure main docs build process can handle all content types (markdown, RST, etc.).

5. **Version Alignment:** Ensure integrated docs reflect current framework version and capabilities.

