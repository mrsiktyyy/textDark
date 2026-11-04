(() => {
  'use strict';

  function initTextDarkSite() {
    // Элементы мобильного меню
    const menuButton = document.getElementById('mobileMenu');
    const navLinks = document.getElementById('navLinks');

    // Открытие и закрытие мобильного меню
    if (menuButton && navLinks) {
      const closeMenu = () => {
        navLinks.classList.remove('open');
        menuButton.setAttribute('aria-expanded', 'false');
        menuButton.setAttribute('aria-label', 'Открыть меню');
      };

      menuButton.addEventListener('click', () => {
        const isOpen = navLinks.classList.toggle('open');

        menuButton.setAttribute('aria-expanded', String(isOpen));
        menuButton.setAttribute(
          'aria-label',
          isOpen ? 'Закрыть меню' : 'Открыть меню'
        );
      });

      navLinks.querySelectorAll('a').forEach((link) => {
        link.addEventListener('click', closeMenu);
      });

      // Закрытие меню клавишей Escape
      document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
          closeMenu();
        }
      });

      // Закрытие при нажатии за пределами меню
      document.addEventListener('click', (event) => {
        const clickedInsideMenu = navLinks.contains(event.target);
        const clickedButton = menuButton.contains(event.target);

        if (!clickedInsideMenu && !clickedButton) {
          closeMenu();
        }
      });
    }

    // Плавное появление элементов при прокрутке
    const revealItems = document.querySelectorAll('.reveal');

    const showAllItems = () => {
      revealItems.forEach((item) => {
        item.classList.add('visible');
      });
    };

    const reducedMotion = window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reducedMotion || !('IntersectionObserver' in window)) {
      showAllItems();
    } else {
      try {
        const revealObserver = new IntersectionObserver(
          (entries, observer) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
              }
            });
          },
          {
            threshold: 0.12,
            rootMargin: '0px 0px -35px 0px'
          }
        );

        revealItems.forEach((item) => {
          revealObserver.observe(item);
        });
      } catch (error) {
        console.warn('textDark: не удалось запустить анимации:', error);
        showAllItems();
      }
    }

    // Подсветка активного пункта навигации
    const sections = document.querySelectorAll('main section[id]');
    const navLinksWithAnchors = document.querySelectorAll(
      '.nav-link[href^="#"]'
    );

    if (
      'IntersectionObserver' in window &&
      sections.length > 0 &&
      navLinksWithAnchors.length > 0
    ) {
      const sectionObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;

            navLinksWithAnchors.forEach((link) => {
              const isActive =
                link.getAttribute('href') === `#${entry.target.id}`;

              link.classList.toggle('active', isActive);
            });
          });
        },
        {
          rootMargin: '-35% 0px -55% 0px'
        }
      );

      sections.forEach((section) => {
        sectionObserver.observe(section);
      });
    }

    console.log('textDark website: JavaScript загружен.');
  }

  // Запуск после готовности HTML
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTextDarkSite, {
      once: true
    });
  } else {
    initTextDarkSite();
  }
})();
