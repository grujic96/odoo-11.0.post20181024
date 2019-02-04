odoo.define('hotel.room.card.filter_button', function (require) {

"use strict";


var core = require('web.core');

var ListController = require('web.ListController');

    ListController.include({

        renderButtons: function($node) {
        this._super.apply(this, arguments);
            if (this.$buttons) {
                let filter_button = this.$buttons.find('.oe_filter_button');
                filter_button && filter_button.click(this.proxy('filter_button')) ;
            }
        },
        filter_button: function () {
        document.getElementById("asdfdsa").classList.className += "myButton2";
        document.getElementById("asdfdsa").classList.className += "myButton1";
            console.log('uspeo')
           // instance.web.Model('sale.order')
           // .call('_get_customer_lead', [[]])
//           return this._rpc({
//            model: 'hotel.room',
//            method: 'find_card_by_card_number',
//            args: ['self'],
//});

//            var self = this;
//            var record = this.model.get(this.handle, {raw: true});
//            return this.model.load({
//            context: record.getContext(),
//            fields: record.fields,
//            fieldsInfo: record.fieldsInfo,
//            modelName: this.modelName,
//            parentID: 'hotel.menu_hotel_room',
//            res_ids: record.res_ids,
//            type: 'record',
//            viewType: 'form',
//        }).then(function (handle) {
//            self.handle = handle;
//            self._updateEnv();
//            return self._setMode('edit');
//        });


        }
    });
    console.log('doso');
    core.action_registry.add('hotel.filter_button', ListController);
    // return the object.
    return ListController;

})