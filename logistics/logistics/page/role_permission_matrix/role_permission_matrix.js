// route: role-permission-matrix
// Thin stub — UI lives in public/js/role_permission_matrix_page.js (hooks page_js).

frappe.provide("logistics.role_permission_matrix");

frappe.pages["role-permission-matrix"].on_page_load = function (wrapper) {
	const ns = logistics.role_permission_matrix;
	if (ns.page) {
		return;
	}
	if (ns.RolePermissionMatrixPage) {
		ns.page = new ns.RolePermissionMatrixPage(wrapper);
		return;
	}
	frappe.require("/assets/logistics/js/role_permission_matrix_page.js?v=5", function () {
		if (!ns.page && ns.RolePermissionMatrixPage) {
			ns.page = new ns.RolePermissionMatrixPage(wrapper);
		}
	});
};

frappe.pages["role-permission-matrix"].on_page_show = function () {
	const page = logistics.role_permission_matrix.page;
	if (page && page.refresh) {
		page.refresh();
	}
};
