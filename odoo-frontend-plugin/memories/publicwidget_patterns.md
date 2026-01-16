# publicWidget JavaScript Patterns

## Basic Pattern

```javascript
/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.MyWidget = publicWidget.Widget.extend({
    selector: '.my-selector',
    disabledInEditableMode: false,  // Handle website builder mode

    events: {
        'click .button': '_onClick',
        'mouseenter .hover-element': '_onMouseEnter',
    },

    /**
     * @override
     */
    start: function () {
        if (!this.editableMode) {
            // Only run in read mode (not in website builder)
            this._initializeWidget();
        }
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    destroy: function () {
        // Clean up event listeners and timers
        this._cleanup();
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private Methods
    //--------------------------------------------------------------------------

    _initializeWidget: function () {
        // Widget initialization logic
    },

    _cleanup: function () {
        // Cleanup logic
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onClick: function (ev) {
        ev.preventDefault();
        // Handle click
    },

    _onMouseEnter: function (ev) {
        // Handle hover
    },
});

export default publicWidget.registry.MyWidget;
```

## editableMode Handling

The `editableMode` property is crucial for website builder compatibility:

```javascript
start: function () {
    if (this.editableMode) {
        // In website builder - show editing UI
        this._setupEditingMode();
    } else {
        // In read mode - show live functionality
        this._setupLiveMode();
    }
    return this._super.apply(this, arguments);
},
```

## Common Patterns

### 1. Animation Widget
```javascript
publicWidget.registry.AnimateOnScroll = publicWidget.Widget.extend({
    selector: '.animate-on-scroll',
    disabledInEditableMode: true,  // Disable in builder

    start: function () {
        this._setupIntersectionObserver();
        return this._super.apply(this, arguments);
    },

    _setupIntersectionObserver: function () {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animated');
                }
            });
        }, { threshold: 0.1 });

        observer.observe(this.el);
        this._observer = observer;
    },

    destroy: function () {
        if (this._observer) {
            this._observer.disconnect();
        }
        return this._super.apply(this, arguments);
    },
});
```

### 2. Counter Widget
```javascript
publicWidget.registry.CounterWidget = publicWidget.Widget.extend({
    selector: '.counter-widget',
    disabledInEditableMode: true,

    start: function () {
        this._animateCounters();
        return this._super.apply(this, arguments);
    },

    _animateCounters: function () {
        this.$('.counter').each((i, el) => {
            const target = parseInt(el.dataset.target, 10);
            this._countUp(el, target);
        });
    },

    _countUp: function (el, target) {
        let current = 0;
        const duration = 2000;
        const step = target / (duration / 16);

        const timer = setInterval(() => {
            current += step;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            el.textContent = Math.floor(current);
        }, 16);
    },
});
```

### 3. Lazy Load Images
```javascript
publicWidget.registry.LazyLoadImages = publicWidget.Widget.extend({
    selector: '.lazy-load-container',
    disabledInEditableMode: true,

    start: function () {
        this._setupLazyLoading();
        return this._super.apply(this, arguments);
    },

    _setupLazyLoading: function () {
        const images = this.$('img[data-src]');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            });
        });

        images.each((i, img) => observer.observe(img));
    },
});
```

## DO NOT Use

- **Inline JavaScript** in templates
- **Owl components** for website themes (use publicWidget)
- **Direct DOM manipulation** without cleanup
- **Global event listeners** without proper removal

## Best Practices

1. Always use `disabledInEditableMode` appropriately
2. Clean up observers, timers, and event listeners in `destroy()`
3. Use `this.$()` for scoped jQuery selections
4. Handle both edit and read modes gracefully
5. Use proper JSDoc comments for methods
