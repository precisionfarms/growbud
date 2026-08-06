import esphome.codegen as cg
import esphome.config_validation as cv

pump_scheduler_ns = cg.esphome_ns.namespace("pump_scheduler")
PumpScheduler = pump_scheduler_ns.class_("PumpScheduler", cg.Component)

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(PumpScheduler),
})

def to_code(config):
    var = cg.new_Pvariable(config[cv.GenerateID()])
    cg.add(var)
