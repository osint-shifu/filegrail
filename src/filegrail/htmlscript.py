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

  function copyText(value, button) {
    var label = button.querySelector('.table-copy-label');
    var original = label ? label.textContent : '';
    function done(copied) {
      button.classList.add(copied ? 'ok' : 'no');
      if (label) { label.textContent = copied ? 'Copied' : 'Copy failed'; }
      if (label) { button.title = label.textContent; }
      setTimeout(function () {
        button.classList.remove('ok', 'no');
        if (label) { label.textContent = original; button.title = original; }
      }, 1000);
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
  }
  document.addEventListener('click', function (event) {
    var button = event.target.closest ? event.target.closest('button.copy') : null;
    if (!button) { return; }
    var value = button.previousElementSibling ? button.previousElementSibling.textContent : '';
    copyText(value, button);
  });
  each(all('button.table-copy'), function (button) {
    button.addEventListener('click', function () {
      var block = button.closest('.table-block');
      var table = block ? block.querySelector('table') : null;
      if (!table) { return; }
      var rows = Array.prototype.filter.call(table.querySelectorAll('tr'), function (row) {
        return !row.hidden;
      });
      var value = rows.map(function (row) {
        return Array.prototype.map.call(row.querySelectorAll('th,td'), function (cell) {
          return cell.textContent.replace(/\\s+/g, ' ').trim();
        }).join('\\t');
      }).join('\\n');
      copyText(value, button);
    });
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

  var timeline = one('.density');
  var timelineRows = Array.prototype.slice.call(all('#timeline-table tbody tr'));
  var timelineShown = one('#timeline-shown');
  var timelineClear = one('#timeline-clear');
  var timelineBin = null;
  function filterTimeline(bin) {
    timelineBin = bin;
    var from = bin ? Number(bin.dataset.from) : -Infinity;
    var to = bin ? Number(bin.dataset.to) : Infinity;
    var day = null;
    var dayHasEvent = false;
    var left = 0;
    timelineRows.forEach(function (row) {
      if (row.classList.contains('day')) {
        if (day) { day.hidden = !dayHasEvent; }
        day = row;
        dayHasEvent = false;
        row.hidden = false;
        return;
      }
      var moment = Number(row.dataset.moment);
      var keep = !bin || (Number.isFinite(moment) && moment >= from && moment <= to);
      row.hidden = !keep;
      if (keep) { left += 1; dayHasEvent = true; }
    });
    if (day) { day.hidden = !dayHasEvent; }
    each(all('.time-bin'), function (mark) {
      var chosen = mark === bin;
      mark.classList.toggle('on', chosen);
      mark.setAttribute('aria-pressed', chosen ? 'true' : 'false');
    });
    if (timeline) { timeline.classList.toggle('filtered', !!bin); }
    if (timelineShown) {
      timelineShown.textContent = left + (left === 1 ? ' dated record' : ' dated records');
    }
    if (timelineClear) { timelineClear.hidden = !bin; }
  }
  each(all('.time-bin'), function (bin) {
    bin.addEventListener('click', function () {
      filterTimeline(timelineBin === bin ? null : bin);
    });
    bin.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter' && event.key !== ' ') { return; }
      event.preventDefault();
      bin.dispatchEvent(new MouseEvent('click', {bubbles: true}));
    });
  });
  if (timelineClear) {
    timelineClear.addEventListener('click', function () { filterTimeline(null); });
  }

  var relationshipRows = Array.prototype.slice.call(all('#relationship-table tbody tr'));
  var relationshipNode = one('#relationship-node');
  var relationshipCount = one('#relationship-shown');
  var relationshipTableFind = one('#relationship-table-find');
  var relationshipSort = one('#relationship-sort');
  var relationshipTableClear = one('#relationship-table-clear');
  var relationshipKind = 'all';
  function filterRelationships() {
    var node = relationshipNode ? relationshipNode.value : '';
    var query = relationshipTableFind ? relationshipTableFind.value.trim().toLowerCase() : '';
    var left = 0;
    relationshipRows.forEach(function (row) {
      var touches = !node || row.dataset.source === node || row.dataset.target === node;
      var ofKind = relationshipKind === 'all' || row.dataset.kind === relationshipKind;
      var hasText = !query || row.textContent.toLowerCase().indexOf(query) !== -1;
      row.hidden = !(touches && ofKind && hasText);
      if (!row.hidden) { left += 1; }
    });
    each(all('[data-rel-kind]'), function (button) {
      var chosen = button.dataset.relKind === relationshipKind;
      button.classList.toggle('on', chosen);
      button.setAttribute('aria-pressed', chosen ? 'true' : 'false');
    });
    if (relationshipCount) {
      relationshipCount.textContent = left;
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
  if (relationshipTableFind) {
    relationshipTableFind.addEventListener('input', filterRelationships);
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
  function sortRelationships() {
    if (!relationshipSort || !relationshipRows.length) { return; }
    var parts = relationshipSort.value.split('-');
    var column = {from: 0, relation: 2, to: 3}[parts[0]];
    var direction = parts[1] === 'desc' ? -1 : 1;
    var body = relationshipRows[0].parentNode;
    relationshipRows.sort(function (a, b) {
      var left = a.children[column].textContent.trim();
      var right = b.children[column].textContent.trim();
      return left.localeCompare(right, undefined, {numeric: true}) * direction;
    }).forEach(function (row) { body.appendChild(row); });
  }
  if (relationshipSort) {
    relationshipSort.addEventListener('change', sortRelationships);
    sortRelationships();
  }
  function restoreNodeOptions() {
    if (finder) { finder.value = ''; }
    if (typeof groups === 'undefined') { return; }
    groups.forEach(function (held) {
      held.options.forEach(function (option) { held.group.appendChild(option); });
      held.group.hidden = false;
    });
  }
  function clearRelationshipFilters() {
    if (relationshipNode) { relationshipNode.value = ''; }
    if (relationshipTableFind) { relationshipTableFind.value = ''; }
    if (relationshipSort) { relationshipSort.value = 'relation-asc'; }
    relationshipKind = 'all';
    restoreNodeOptions();
    filterRelationships();
    sortRelationships();
  }
  if (relationshipTableClear) {
    relationshipTableClear.addEventListener('click', clearRelationshipFilters);
  }
  document.addEventListener('click', function (event) {
    if (!event.target.closest || !relationshipNode) { return; }
    var focus = event.target.closest('[data-rel-focus]');
    if (!focus) { return; }
    relationshipNode.value = focus.dataset.relFocus;
    relationshipKind = 'all';
    filterRelationships();
    var graphMark = focus.classList.contains('node') ? focus : null;
    if (!graphMark) {
      each(all('.graph .node'), function (mark) {
        if (mark.dataset.graphNode === focus.dataset.relFocus) { graphMark = mark; }
      });
    }
    if (graphMark) { showGraphDetail(graphMark); }
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

  var graph = one('#evidence-graph');
  var graphViewport = graph ? graph.querySelector('.graph-viewport') : null;
  var graphZoomValue = one('#graph-zoom-value');
  var graphInspector = one('#graph-inspector');
  var graphDetail = one('#graph-detail');
  var graphDetailClose = one('#graph-detail-close');
  var graphScale = 1;
  var graphX = 0;
  var graphY = 0;
  var graphDrag = null;
  function graphPoint(event) {
    var box = graph.getBoundingClientRect();
    var view = graph.viewBox.baseVal;
    return {
      x: (event.clientX - box.left) * view.width / box.width,
      y: (event.clientY - box.top) * view.height / box.height
    };
  }
  function drawGraphView() {
    if (!graphViewport) { return; }
    graphViewport.setAttribute(
      'transform',
      'translate(' + graphX.toFixed(2) + ' ' + graphY.toFixed(2) + ') scale('
        + graphScale.toFixed(4) + ')'
    );
    if (graphZoomValue) { graphZoomValue.textContent = Math.round(graphScale * 100) + '%'; }
  }
  function zoomGraph(factor, centre) {
    if (!graph) { return; }
    var view = graph.viewBox.baseVal;
    centre = centre || {x: view.width / 2, y: view.height / 2};
    var scale = Math.max(0.5, Math.min(4, graphScale * factor));
    graphX = centre.x - (centre.x - graphX) * scale / graphScale;
    graphY = centre.y - (centre.y - graphY) * scale / graphScale;
    graphScale = scale;
    drawGraphView();
  }
  function fitGraph() {
    if (!graph || !graphViewport) { return; }
    var bounds = graphViewport.getBBox();
    if (!bounds.width || !bounds.height) { return; }
    var view = graph.viewBox.baseVal;
    var pad = 34;
    graphScale = Math.max(0.5, Math.min(2.5,
      Math.min((view.width - 2 * pad) / bounds.width, (view.height - 2 * pad) / bounds.height)));
    graphX = view.width / 2 - (bounds.x + bounds.width / 2) * graphScale;
    graphY = view.height / 2 - (bounds.y + bounds.height / 2) * graphScale;
    drawGraphView();
  }
  function inspectGraphNode(mark) {
    if (!graphInspector) { return; }
    var title = mark ? mark.querySelector('title') : null;
    graphInspector.textContent = title ? title.textContent : 'Drag to pan · scroll to zoom';
  }
  function graphDetailText(id, value) {
    var field = one(id);
    if (field) { field.textContent = value || '·'; }
  }
  function showGraphDetail(mark) {
    if (!graphDetail || !mark) { return; }
    var file = !!mark.dataset.fileRef;
    graphDetail.hidden = false;
    graphDetailText('#graph-detail-type', mark.dataset.nodeType);
    graphDetailText('#graph-detail-value', mark.dataset.nodeValue);
    graphDetailText('#graph-detail-degree', mark.dataset.nodeDegree);
    graphDetailText('#graph-detail-file',
      file ? mark.dataset.fileRef + ' ' + mark.dataset.fileName : '');
    graphDetailText('#graph-detail-path', mark.dataset.filePath);
    graphDetailText('#graph-detail-format', mark.dataset.fileFormat);
    graphDetailText('#graph-detail-size', mark.dataset.fileSize);
    graphDetailText('#graph-detail-modified', mark.dataset.fileModified);
    graphDetailText('#graph-detail-evidence', mark.dataset.fileEvidence);
    graphDetailText('#graph-detail-state', mark.dataset.fileState);
    graphDetailText('#graph-detail-origin', mark.dataset.fileOrigin);
    each(graphDetail.querySelectorAll('.file-only'), function (field) { field.hidden = !file; });
    var open = one('#graph-detail-open');
    if (open && file) { open.setAttribute('href', mark.dataset.fileLink); }
    var pivot = one('#graph-detail-pivot');
    if (pivot) {
      pivot.hidden = !mark.dataset.pivotLink;
      if (mark.dataset.pivotLink) { pivot.setAttribute('href', mark.dataset.pivotLink); }
    }
    var connected = one('#graph-detail-connected');
    if (connected) {
      connected.textContent = '';
      var id = mark.dataset.graphNode;
      relationshipRows.forEach(function (row) {
        var out = row.dataset.source === id;
        if (!out && row.dataset.target !== id) { return; }
        var other = row.children[out ? 3 : 0].querySelector('.rel-node');
        if (!other) { return; }
        var item = document.createElement('li');
        var kind = document.createElement('span');
        kind.className = 'kind';
        kind.textContent = (out ? '' : '\u2190 ') + row.dataset.kind + (out ? ' \u2192' : '');
        item.appendChild(kind);
        item.appendChild(other.cloneNode(true));
        connected.appendChild(item);
      });
      connected.parentNode.hidden = !connected.childNodes.length;
    }
  }
  if (graphDetailClose) {
    graphDetailClose.addEventListener('click', function () { graphDetail.hidden = true; });
  }
  if (graph) {
    graph.addEventListener('wheel', function (event) {
      event.preventDefault();
      zoomGraph(event.deltaY < 0 ? 1.15 : 1 / 1.15, graphPoint(event));
    }, {passive: false});
    graph.addEventListener('pointerdown', function (event) {
      if (event.target.closest && event.target.closest('.node')) { return; }
      graphDrag = graphPoint(event);
      graph.setPointerCapture(event.pointerId);
      graph.classList.add('dragging');
    });
    graph.addEventListener('pointermove', function (event) {
      var mark = event.target.closest ? event.target.closest('.node') : null;
      if (!graphDrag) { inspectGraphNode(mark); return; }
      var point = graphPoint(event);
      graphX += point.x - graphDrag.x;
      graphY += point.y - graphDrag.y;
      graphDrag = point;
      drawGraphView();
    });
    graph.addEventListener('pointerup', function (event) {
      graphDrag = null;
      graph.releasePointerCapture(event.pointerId);
      graph.classList.remove('dragging');
    });
    graph.addEventListener('pointercancel', function () {
      graphDrag = null;
      graph.classList.remove('dragging');
    });
    graph.addEventListener('focusin', function (event) {
      inspectGraphNode(event.target.closest ? event.target.closest('.node') : null);
    });
    graph.addEventListener('mouseleave', function () {
      inspectGraphNode(graph.querySelector('.node.on'));
    });
    graph.addEventListener('keydown', function (event) {
      var step = 28;
      if (event.key === '+' || event.key === '=') { zoomGraph(1.2); }
      else if (event.key === '-') { zoomGraph(1 / 1.2); }
      else if (event.key === '0') { fitGraph(); }
      else if (event.key === 'ArrowLeft') { graphX += step; drawGraphView(); }
      else if (event.key === 'ArrowRight') { graphX -= step; drawGraphView(); }
      else if (event.key === 'ArrowUp') { graphY += step; drawGraphView(); }
      else if (event.key === 'ArrowDown') { graphY -= step; drawGraphView(); }
      else { return; }
      event.preventDefault();
    });
  }
  var graphZoomOut = one('#graph-zoom-out');
  var graphZoomIn = one('#graph-zoom-in');
  var graphFit = one('#graph-fit');
  var graphExport = one('#graph-export');
  var graphReset = one('#graph-reset');
  if (graphZoomOut) {
    graphZoomOut.addEventListener('click', function () { zoomGraph(1 / 1.2); });
  }
  if (graphZoomIn) {
    graphZoomIn.addEventListener('click', function () { zoomGraph(1.2); });
  }
  if (graphFit) { graphFit.addEventListener('click', fitGraph); }
  if (graphExport && graph) {
    graphExport.addEventListener('click', function () {
      var clone = graph.cloneNode(true);
      var palette = getComputedStyle(root);
      var colour = function (name) { return palette.getPropertyValue(name).trim(); };
      var style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
      style.textContent = 'svg{background:' + colour('--surface') + '}'
        + '.e{stroke:' + colour('--line-2') + ';stroke-width:1;stroke-opacity:.9}'
        + '.node circle{fill:' + colour('--faint') + ';stroke:' + colour('--surface')
        + ';stroke-width:1.5}.t-file circle{fill:' + colour('--accent') + '}'
        + '.t-person circle,.t-org circle,.t-handle circle{fill:' + colour('--activity') + '}'
        + '.t-device circle,.t-camera_model circle{fill:' + colour('--metadata') + '}'
        + 'text{font:10px ui-monospace,monospace;fill:' + colour('--ink-2')
        + ';text-anchor:middle;paint-order:stroke;stroke:' + colour('--surface')
        + ';stroke-width:3px;stroke-linejoin:round}.focused .node:not(.on):not(.near){opacity:.2}'
        + '.focused .e{stroke-opacity:.1}.focused .e.on{stroke:' + colour('--accent')
        + ';stroke-opacity:1;stroke-width:1.5}';
      clone.insertBefore(style, clone.firstChild);
      clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
      clone.setAttribute('width', graph.viewBox.baseVal.width);
      clone.setAttribute('height', graph.viewBox.baseVal.height);
      clone.removeAttribute('tabindex');
      if (graph.closest('.graph').classList.contains('focused')) {
        clone.classList.add('focused');
      }
      var source = new XMLSerializer().serializeToString(clone);
      var url = URL.createObjectURL(new Blob([source], {type: 'image/svg+xml'}));
      var link = document.createElement('a');
      link.href = url;
      link.download = 'filegrail-evidence-graph.svg';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(function () { URL.revokeObjectURL(url); }, 0);
    });
  }
  if (graphReset) {
    graphReset.addEventListener('click', function () {
      clearRelationshipFilters();
      if (graphDetail) { graphDetail.hidden = true; }
      inspectGraphNode(null);
      fitGraph();
    });
  }
  if (graph) { window.requestAnimationFrame(fitGraph); }

  var toTop = one('#to-top');
  if (toTop) {
    var placeTop = function () { toTop.hidden = window.scrollY < 600; };
    window.addEventListener('scroll', placeTop, {passive: true});
    placeTop();
    toTop.addEventListener('click', function () { window.scrollTo({top: 0}); });
  }

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
