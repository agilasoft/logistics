// Document checklist for Permission Studio.
// Selection is kept separately from the search text, so clearing the search
// does not uncheck a document. The caller shows viewport_rows at a time and
// scrolls for the rest. Tagged documents stay in the list with an indicator.

(function (root, factory) {
	const api = factory();
	if (typeof module !== "undefined" && module.exports) {
		module.exports = api;
	}
	if (root) {
		root.logistics = root.logistics || {};
		root.logistics.permission_studio_picker = api;
	}
})(typeof window !== "undefined" ? window : globalThis, function () {
	const PICKER_PAGE_SIZE = 25;

	function clean(value) {
		return String(value || "").replace(/\s+/g, " ").trim();
	}

	function nameOf(doc) {
		if (typeof doc === "string") {
			return clean(doc);
		}
		return clean(doc && doc.name);
	}

	function labelOf(doc) {
		if (typeof doc === "string") {
			return clean(doc);
		}
		return clean((doc && (doc.label || doc.name)) || "");
	}

	function matches(doc, query) {
		if (!query) {
			return true;
		}
		const hay = [doc.name, doc.label, doc.description].map(clean).join(" ").toLowerCase();
		return hay.indexOf(query) !== -1;
	}

	function toggleSelected(selected, document, checked) {
		const name = nameOf(document);
		const next = [];
		const seen = {};
		(selected || []).forEach(function (item) {
			const itemName = nameOf(item);
			if (!itemName || itemName === name || seen[itemName]) {
				return;
			}
			seen[itemName] = true;
			next.push(typeof item === "string" ? { name: itemName, label: itemName, tags: [] } : item);
		});
		if (checked && name) {
			const source = typeof document === "string" ? { name: name, label: name, tags: [] } : document || {};
			next.push({
				name: name,
				label: labelOf(source) || name,
				description: clean(source.description),
				tags: (source.tags || []).slice(),
			});
		}
		return next;
	}

	function pickerView(options) {
		const opts = options || {};
		const pageSize = opts.pageSize > 0 ? opts.pageSize : PICKER_PAGE_SIZE;
		const query = clean(opts.query).toLowerCase();
		const selectedDocs = [];
		const selectedNames = {};
		(opts.selected || []).forEach(function (item) {
			const name = nameOf(item);
			if (!name || selectedNames[name]) {
				return;
			}
			selectedNames[name] = true;
			if (typeof item === "string") {
				selectedDocs.push({ name: name, label: name, description: "", tags: [] });
			} else {
				selectedDocs.push({
					name: name,
					label: labelOf(item) || name,
					description: clean(item.description),
					tags: (item.tags || []).slice(),
				});
			}
		});

		const tagsByName = {};
		function collectTags(doc) {
			const name = nameOf(doc);
			if (!name || !doc || !doc.tags) {
				return;
			}
			tagsByName[name] = tagsByName[name] || [];
			doc.tags.forEach(function (tag) {
				const serialized = JSON.stringify(tag);
				const exists = tagsByName[name].some(function (current) {
					return JSON.stringify(current) === serialized;
				});
				if (!exists) {
					tagsByName[name].push(tag);
				}
			});
		}
		(opts.tagged || []).forEach(collectTags);
		(opts.documents || []).forEach(collectTags);

		const rows = [];
		const seen = {};

		function add(doc, checked, source) {
			const name = nameOf(doc);
			if (!name || seen[name]) {
				return;
			}
			if (source !== "selected" && !matches(doc, query)) {
				return;
			}
			seen[name] = true;
			const tags = (doc.tags || []).slice();
			(tagsByName[name] || []).forEach(function (tag) {
				const serialized = JSON.stringify(tag);
				if (!tags.some(function (current) { return JSON.stringify(current) === serialized; })) {
					tags.push(tag);
				}
			});
			rows.push({
				name: name,
				label: labelOf(doc) || name,
				description: clean(doc.description),
				checked: !!(checked || selectedNames[name]),
				tags: tags,
				source: source,
			});
		}

		selectedDocs.forEach(function (doc) {
			add(doc, true, "selected");
		});
		(opts.tagged || []).forEach(function (doc) {
			add(doc, !!selectedNames[nameOf(doc)], "tagged");
		});
		(opts.documents || []).forEach(function (doc) {
			add(doc, false, "document");
		});

		return {
			rows: rows,
			total: rows.length,
			selected: selectedDocs.map(function (doc) { return doc.name; }),
			selectedCount: selectedDocs.length,
			pageSize: pageSize,
			viewportRows: pageSize,
		};
	}

	return {
		PICKER_PAGE_SIZE: PICKER_PAGE_SIZE,
		pickerView: pickerView,
		toggleSelected: toggleSelected,
	};
});
