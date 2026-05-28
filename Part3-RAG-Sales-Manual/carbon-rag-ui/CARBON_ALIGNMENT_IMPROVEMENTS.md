# Carbon Design System Alignment Improvements

## Overview
This document outlines the improvements made to align the RAG UI with IBM Carbon Design System standards and best practices, based on the better-aligned Carbon GenAI Demos implementation.

## Issues Identified

### 1. Missing Shared Styling Architecture
**Problem:** No reusable mixins or overrides files for consistent styling patterns.
**Impact:** Inconsistent styling and difficulty maintaining Carbon standards.

### 2. Inconsistent Spacing
**Problem:** Banner padding didn't follow Carbon's spacing scale properly.
**Impact:** Visual inconsistency with other Carbon applications.

### 3. Layout Structure Issues
**Problem:** Missing negative margins for full-bleed sections, causing content to not extend to viewport edges.
**Impact:** Content appeared cramped and didn't match Carbon's grid system expectations.

### 4. Tab Content Padding
**Problem:** Tab panels didn't follow Carbon's recommended padding patterns.
**Impact:** Inconsistent spacing within tabbed content areas.

### 5. Grid Nesting
**Problem:** Unnecessary nested Grid components causing extra spacing.
**Impact:** Excessive whitespace and layout inconsistencies.

## Improvements Implemented

### 1. Created Shared Styling Files

#### `_mixins.scss`
```scss
@use '@carbon/react/scss/spacing' as *;
@use '@carbon/react/scss/breakpoint' as *;

@mixin landing-page-background() {
  background-color: $layer-01;
  position: relative;
  padding-top: $spacing-05;
  padding-bottom: $spacing-07 * 4;

  @include breakpoint-down(md) {
    padding-top: $spacing-04;
    padding-bottom: $spacing-07 * 4;
  }
}
```

**Purpose:** Provides reusable mixins for consistent page backgrounds and spacing.

#### `_overrides.scss`
```scss
@use '@carbon/react/scss/spacing' as *;
@use '@carbon/react/scss/theme' as *;

.cds--tabs--scrollable .cds--tabs--scrollable__nav-link {
  padding: $spacing-04 $spacing-05;
}

.cds--tab-content {
  padding: $spacing-05 0;
}
```

**Purpose:** Provides Carbon component overrides for consistent tab styling.

### 2. Updated Page Styling (`_sales-manual-page.scss`)

#### Added Proper Imports
```scss
@use '@carbon/react/scss/breakpoint' as *;
@use './mixins.scss' as *;
@use './overrides.scss';
```

#### Improved Banner Spacing
```scss
.rag-page__banner {
  padding-top: $spacing-05;
  padding-bottom: $spacing-07 * 4;  // Changed from $spacing-07
  padding-left: $spacing-06;
}
```

#### Added Negative Margins for Full-Bleed
```scss
.rag-page__banner,
.rag-page__r2,
.rag-page__content {
  margin-left: -20px;
  margin-right: -20px;

  @include breakpoint-down(md) {
    margin-left: 0;
    margin-right: 0;
  }
}
```

**Purpose:** Allows content to extend to viewport edges on larger screens while maintaining proper spacing on mobile.

#### Added Tab Content Styling
```scss
.tabs-group {
  background-color: $layer-01;
  padding: 0 0;
  margin-bottom: 0;
}

.tabs-group-content {
  padding: $spacing-10 0 0 $spacing-06;
  padding-bottom: 0;
}

/* Remove bottom margin on last grid row */
.tabs-group-content :where(.cds--row:last-child, .cds--subgrid-row:last-child) {
  margin-bottom: 0;
}
```

**Purpose:** Ensures consistent spacing within tab panels and removes unwanted bottom margins.

#### Added Typography Styles
```scss
.rag-page__subheading {
  @include type-style('productive-heading-03');
  font-weight: 600;
}

.rag-page__p {
  @include type-style('productive-heading-03');
  margin-top: $spacing-06;
  margin-bottom: 0;

  @include breakpoint-between((320px + 1), md) {
    max-width: 75%;
  }
}

.rag-page__label {
  @include type-style('heading-01');

  @include breakpoint-down(md) {
    padding-bottom: 1.5rem;
  }
}
```

**Purpose:** Provides consistent typography hierarchy following Carbon type styles.

### 3. Updated Page Component (`page.js`)

#### Simplified Grid Structure
**Before:**
```jsx
<>
  <Grid className="rag-page" fullWidth>
    <Column lg={16} md={8} sm={4} className="rag-page__banner">
      {/* Banner content */}
    </Column>
  </Grid>
  
  <Grid fullWidth>
    <Column lg={16} md={8} sm={4} className="rag-page__content">
      <Tabs>
        {/* Tabs content */}
      </Tabs>
    </Column>
  </Grid>
</>
```

**After:**
```jsx
<Grid className="rag-page" fullWidth>
  <Column lg={16} md={8} sm={4} className="rag-page__banner">
    {/* Banner content */}
  </Column>

  <Column lg={16} md={8} sm={4} className="rag-page__r2">
    <Tabs>
      {/* Tabs content */}
    </Tabs>
  </Column>
</Grid>
```

**Benefits:**
- Single Grid container reduces nesting complexity
- Proper use of `rag-page__r2` class for negative margin offset
- Cleaner component hierarchy

#### Added Tab Content Classes
```jsx
<TabPanel>
  <Grid className="tabs-group-content">
    {/* Tab content */}
  </Grid>
</TabPanel>
```

**Purpose:** Applies consistent padding and spacing to tab panel content.

#### Improved Breadcrumb Structure
```jsx
<Breadcrumb noTrailingSlash aria-label="Page navigation">
  <BreadcrumbItem>
    <a href="/">Home</a>
  </BreadcrumbItem>
</Breadcrumb>
```

**Benefits:**
- Added proper `aria-label` for accessibility
- Simplified breadcrumb structure

## Carbon Design System Principles Applied

### 1. **Spacing Scale**
- Uses Carbon's spacing tokens (`$spacing-05`, `$spacing-07`, etc.)
- Consistent spacing throughout the application
- Proper use of spacing multipliers (e.g., `$spacing-07 * 4`)

### 2. **Grid System**
- Proper use of negative margins for full-bleed sections
- Responsive breakpoints using Carbon's breakpoint mixins
- Consistent column widths across viewports

### 3. **Typography**
- Uses Carbon type styles (`productive-heading-05`, `heading-01`, etc.)
- Consistent font weights and sizes
- Proper type hierarchy

### 4. **Layering**
- Uses Carbon layer tokens (`$layer-01`, `$layer-02`)
- Proper background colors for different UI levels
- Consistent use of theme tokens

### 5. **Component Patterns**
- Follows Carbon's tab component patterns
- Proper use of Grid and Column components
- Consistent component nesting

## Testing Recommendations

1. **Visual Testing**
   - Compare with Carbon GenAI Demos for consistency
   - Test on multiple screen sizes (mobile, tablet, desktop)
   - Verify spacing matches Carbon specifications

2. **Accessibility Testing**
   - Verify aria labels are present
   - Test keyboard navigation
   - Check color contrast ratios

3. **Responsive Testing**
   - Test breakpoint transitions
   - Verify negative margins work correctly
   - Check mobile layout

4. **Browser Testing**
   - Test in Chrome, Firefox, Safari, Edge
   - Verify CSS Grid support
   - Check for any layout issues

## Next Steps

1. Apply similar improvements to other pages (e.g., Harry Potter RAG page)
2. Consider creating a shared layout component for consistent page structure
3. Document any additional Carbon patterns used in the application
4. Review and update other components for Carbon alignment

## References

- [Carbon Design System Documentation](https://carbondesignsystem.com/)
- [Carbon React Components](https://react.carbondesignsystem.com/)
- [Carbon Design Kit](https://www.carbondesignsystem.com/designing/kits/sketch)
- Carbon GenAI Demos implementation (reference project)

## Made with Bob