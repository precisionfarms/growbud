import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID


growbud_ns = cg.esphome_ns.namespace("growbud")
GrowBudComponent = growbud_ns.class_("GrowBudComponent", cg.Component)

CONFIG_SCHEMA = cv.Schema(
    {cv.GenerateID(): cv.declare_id(GrowBudComponent)}
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
