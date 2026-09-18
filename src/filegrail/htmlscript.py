"""The script of the HTML report, written into the page.

Plain browser JavaScript with no build step and no dependency, inline for
the same reason the stylesheet is: the page must work as one file, offline.
"""

from __future__ import annotations

SCRIPT = """
(function () {
  var root = document.documentElement;
  root.classList.add('js');
  var each = function (list, visit) { Array.prototype.forEach.call(list, visit); };
  var one = function (selector) { return document.querySelector(selector); };
  var all = function (selector) { return document.querySelectorAll(selector); };

  var theme = one('#theme');
  function wear(name) {
    root.setAttribute('data-theme', name);
    theme.title = name === 'light' ? 'Dark theme' : 'Light theme';
    theme.setAttribute('aria-label', theme.title);
    try { localStorage.setItem('filegrail-theme', name); } catch (error) { /* private mode */ }
  }
  if (theme) {
    var kept = null;
    try { kept = localStorage.getItem('filegrail-theme'); } catch (error) { kept = null; }
    var prefersLight = window.matchMedia
      && window.matchMedia('(prefers-color-scheme: light)').matches;
    wear(kept === 'light' || (kept === null && prefersLight) ? 'light' : 'dark');
    theme.addEventListener('click', function () {
      wear(root.getAttribute('data-theme') === 'light' ? 'dark' : 'light');
    });
  }
  var printer = one('#print');
  if (printer) { printer.addEventListener('click', function () { window.print(); }); }
  // A closed block prints closed whatever the stylesheet says, because the
  // browser keeps its contents out of the layout. Open them for the printer
  // and close them again afterwards.
  var unfolded = [];
  window.addEventListener('beforeprint', function () {
    unfolded = Array.prototype.filter.call(all('details'), function (block) {
      return !block.open;
    });
    unfolded.forEach(function (block) { block.open = true; });
  });
  window.addEventListener('afterprint', function () {
    unfolded.forEach(function (block) { block.open = false; });
    unfolded = [];
  });

  document.addEventListener('click', function (event) {
    var button = event.target.closest ? event.target.closest('button.copy') : null;
    if (!button) { return; }
    var value = button.previousElementSibling ? button.previousElementSibling.textContent : '';
    function done(copied) {
      button.classList.add(copied ? 'ok' : 'no');
      setTimeout(function () { button.classList.remove('ok', 'no'); }, 1000);
    }
    function fallback() {
      var area = document.createElement('textarea');
      area.value = value;
      document.body.appendChild(area);
      area.select();
      var copied = false;
      try { copied = document.execCommand('copy'); } catch (error) { copied = false; }
      document.body.removeChild(area);
      done(copied);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(value).then(function () { done(true); }, fallback);
    } else {
      fallback();
    }
  });

  var rows = Array.prototype.slice.call(all('#index tbody tr'));
  var counted = one('#shown');
  function filter(wanted) {
    each(all('.chip'), function (chip) {
      chip.classList.toggle('on', chip.dataset.filter === wanted);
    });
    var left = 0;
    rows.forEach(function (row) {
      var keep = wanted === 'all' || (row.dataset.f || '').split(' ').indexOf(wanted) !== -1;
      row.hidden = !keep;
      if (keep) { left += 1; }
    });
    if (counted) { counted.textContent = left; }
  }
  document.addEventListener('click', function (event) {
    if (!event.target.closest) { return; }
    var chip = event.target.closest('[data-filter]');
    if (chip) { filter(chip.dataset.filter); }
  });

  var relationshipRows = Array.prototype.slice.call(all('#relationship-table tbody tr'));
  var relationshipNode = one('#relationship-node');
  var relationshipCount = one('#relationship-shown');
  var relationshipKind = 'all';
  function filterRelationships() {
    var node = relationshipNode ? relationshipNode.value : '';
    var left = 0;
    relationshipRows.forEach(function (row) {
      var touches = !node || row.dataset.source === node || row.dataset.target === node;
      var ofKind = relationshipKind === 'all' || row.dataset.kind === relationshipKind;
      row.hidden = !(touches && ofKind);
      if (!row.hidden) { left += 1; }
    });
    each(all('[data-rel-kind]'), function (button) {
      var chosen = button.dataset.relKind === relationshipKind;
      button.classList.toggle('on', chosen);
      button.setAttribute('aria-pressed', chosen ? 'true' : 'false');
    });
    if (relationshipCount) {
      relationshipCount.textContent = left + (left === 1 ? ' relationship' : ' relationships');
    }
    var figure = one('.graph');
    if (figure) {
      figure.classList.toggle('focused', !!node);
      var near = {};
      each(figure.querySelectorAll('.e'), function (edge) {
        var hit = !!node && (edge.dataset.source === node || edge.dataset.target === node);
        edge.classList.toggle('on', hit);
        if (hit) { near[edge.dataset.source] = true; near[edge.dataset.target] = true; }
      });
      each(figure.querySelectorAll('.node'), function (mark) {
        mark.classList.toggle('on', mark.dataset.graphNode === node);
        mark.classList.toggle('near', !!near[mark.dataset.graphNode]);
      });
    }
  }
  if (relationshipNode) {
    relationshipNode.addEventListener('change', filterRelationships);
  }
  var finder = one('#relationship-find');
  if (finder && relationshipNode) {
    var groups = Array.prototype.map.call(relationshipNode.querySelectorAll('optgroup'),
      function (group) {
        var options = Array.prototype.slice.call(group.querySelectorAll('option'));
        return {group: group, options: options};
      });
    finder.addEventListener('input', function () {
      var wanted = finder.value.trim().toLowerCase();
      var kept = [];
      groups.forEach(function (held) {
        held.options.forEach(function (option) { option.remove(); });
        held.options.forEach(function (option) {
          if (!wanted || option.textContent.toLowerCase().indexOf(wanted) !== -1) {
            held.group.appendChild(option);
            kept.push(option);
          }
        });
        held.group.hidden = !held.group.querySelector('option');
      });
      if (kept.length === 1) {
        relationshipNode.value = kept[0].value;
      } else if (relationshipNode.selectedIndex === -1) {
        relationshipNode.value = '';
      }
      filterRelationships();
    });
  }
  each(all('[data-rel-kind]'), function (button) {
    button.addEventListener('click', function () {
      relationshipKind = button.dataset.relKind;
      filterRelationships();
    });
  });
  document.addEventListener('click', function (event) {
    if (!event.target.closest || !relationshipNode) { return; }
    var focus = event.target.closest('[data-rel-focus]');
    if (!focus) { return; }
    relationshipNode.value = focus.dataset.relFocus;
    relationshipKind = 'all';
    filterRelationships();
    if (!focus.classList.contains('node')) { relationshipNode.focus(); }
  });
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Enter' && event.key !== ' ') { return; }
    var mark = event.target.closest ? event.target.closest('.graph .node') : null;
    if (mark) {
      event.preventDefault();
      mark.dispatchEvent(new MouseEvent('click', {bubbles: true}));
    }
  });
  filterRelationships();

  function show(name) {
    each(all('.tabs button'), function (tab) {
      var chosen = tab.dataset.panel === name;
      tab.classList.toggle('on', chosen);
      tab.setAttribute('aria-selected', chosen ? 'true' : 'false');
    });
    each(all('.pane'), function (pane) { pane.classList.toggle('on', pane.id === name); });
  }
  each(all('.tabs button'), function (tab) {
    tab.addEventListener('click', function () { show(tab.dataset.panel); });
  });

  each(all('.tbl th[data-sort]'), function (head) {
    head.tabIndex = 0;
    function sort() {
      var table = head.closest('table');
      var body = table.tBodies[0];
      var column = Array.prototype.indexOf.call(head.parentNode.children, head);
      var numeric = head.dataset.sort === 'num';
      var rising = head.dataset.dir !== 'asc';
      each(table.querySelectorAll('th'), function (other) {
        delete other.dataset.dir;
        var arrow = other.querySelector('.dir');
        if (arrow) { arrow.remove(); }
      });
      head.dataset.dir = rising ? 'asc' : 'desc';
      head.insertAdjacentHTML('beforeend',
        '<span class="dir">' + (rising ? '\\u25B2' : '\\u25BC') + '</span>');
      function key(row) {
        var cell = row.children[column];
        if (!cell) { return numeric ? 0 : ''; }
        if (numeric) { return parseFloat(cell.dataset.value || 0) || 0; }
        return cell.textContent.trim().toLowerCase();
      }
      Array.prototype.slice.call(body.rows).sort(function (a, b) {
        var x = key(a), y = key(b);
        var order = numeric
          ? x - y
          : String(x).localeCompare(String(y), undefined, {numeric: true});
        return rising ? order : -order;
      }).forEach(function (row) { body.appendChild(row); });
    }
    head.addEventListener('click', sort);
    head.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); sort(); }
    });
  });

  var box = one('#search');
  var hits = one('#hits');
  function searchable() {
    return rows.concat(
      Array.prototype.slice.call(all('.find')),
      Array.prototype.slice.call(all('.conf')),
      Array.prototype.slice.call(all('.rec')),
      Array.prototype.slice.call(all('.pivot')),
      Array.prototype.slice.call(all('.event')),
      Array.prototype.slice.call(all('.relationship'))
    );
  }
  if (box) {
    box.addEventListener('input', function () {
      var wanted = box.value.trim().toLowerCase();
      var found = 0;
      var pane = null;
      if (wanted && relationshipNode) {
        relationshipNode.value = '';
        relationshipKind = 'all';
        filterRelationships();
      }
      searchable().forEach(function (item) {
        item.classList.remove('hit');
        if (!wanted) { return; }
        if (item.textContent.toLowerCase().indexOf(wanted) === -1) { return; }
        item.classList.add('hit');
        found += 1;
        var block = item.closest('details');
        if (block) { block.open = true; }
        var holder = item.closest('.pane');
        if (holder && !pane) { pane = holder.id; }
      });
      if (pane) { show(pane); }
      if (hits) { hits.textContent = wanted ? found + ' hits' : ''; }
      if (!wanted) { filter('all'); return; }
      var left = 0;
      rows.forEach(function (row) {
        row.hidden = !row.classList.contains('hit');
        if (!row.hidden) { left += 1; }
      });
      if (counted) { counted.textContent = left; }
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === '/' && document.activeElement !== box) {
        event.preventDefault();
        box.focus();
      }
      if (event.key === 'Escape' && document.activeElement === box) {
        box.value = '';
        box.dispatchEvent(new Event('input'));
        box.blur();
      }
    });
  }

  var links = Array.prototype.slice.call(all('.nav a[href^="#"]'));
  if (window.IntersectionObserver) {
    var watch = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) { return; }
        links.forEach(function (link) {
          link.classList.toggle('on', link.getAttribute('href') === '#' + entry.target.id);
        });
      });
    }, {rootMargin: '-45% 0px -50% 0px'});
    links.forEach(function (link) {
      var section = document.getElementById(link.getAttribute('href').slice(1));
      if (section) { watch.observe(section); }
    });
  }

  var top = document.getElementById('top');
  var bar = document.querySelector('.nav');
  if (top && bar && window.IntersectionObserver) {
    new IntersectionObserver(function (entries) {
      bar.classList.toggle('scrolled', !entries[0].isIntersecting);
    }, {threshold: 0}).observe(top);
  }

  function opened() {
    if (!location.hash) { return; }
    var target = document.getElementById(location.hash.slice(1));
    if (!target) { return; }
    var block = target.closest('details');
    if (block) { block.open = true; }
    var holder = target.closest('.pane');
    if (holder) { show(holder.id); }
  }
  window.addEventListener('hashchange', opened);
  opened();
})();
"""

#: Section key, the heading it prints, and the short word the nav gives it.
