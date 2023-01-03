/** @odoo-module */

import {registry} from "@web/core/registry";
import {download} from "@web/core/network/download";

async function executeAccountReportDownloadPragmaticKardex({env, action}) {
    env.services.ui.block();
    const url = "/pragmatickardex";
    const data = action.data;
    try {
        await download({url, data});
    } finally {
        env.services.ui.unblock();
    }
}

registry
    .category("action_handlers")
    .add('kardex_xlsx_txt', executeAccountReportDownloadPragmaticKardex);
