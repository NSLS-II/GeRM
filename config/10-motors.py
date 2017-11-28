"Define all the motors on the beamline"

from ophyd import EpicsMotor

th_cal = EpicsMotor('XF:28IDC-ES:1{Dif:2-Ax:Th}Mtr', name='th_cal')
tth_cal = EpicsMotor('XF:28IDC-ES:1{Dif:2-Ax:2Th}Mtr', name='tth_cal')

# Tim test with Sanjit. Delete it if anything goes wrong
ss_stg2_x = EpicsMotor('XF:28IDC-ES:1{Stg:Smpl2-Ax:X}Mtr', name='ss_stg2_x')
# Sanjit Inlcuded this. Delete it if anything goes wrong
ss_stg2_y = EpicsMotor('XF:28IDC-ES:1{Stg:Smpl2-Ax:Y}Mtr', name='ss_stg2_y')
ss_stg2_z = EpicsMotor('XF:28IDC-ES:1{Stg:Smpl2-Ax:Z}Mtr', name='ss_stg2_z')

# RPI DIFFRACTOMETER motors ### Change th only after changing in other plans
th = EpicsMotor('XF:28IDC-ES:1{Dif:1-Ax:Th}Mtr', name='th')
tth = EpicsMotor('XF:28IDC-ES:1{Dif:1-Ax:2ThI}Mtr', name='tth')
diff_x = EpicsMotor('XF:28IDC-ES:1{Dif:1-Ax:X}Mtr', name='diff_x')
diff_y = EpicsMotor('XF:28IDC-ES:1{Dif:1-Ax:Y}Mtr', name='diff_y')
diff_tth_i = EpicsMotor('XF:28IDC-ES:1{Dif:1-Ax:2ThI}Mtr', name='diff_tth_i')
diff_tth_o = EpicsMotor('XF:28IDC-ES:1{Dif:1-Ax:2ThO}Mtr', name='diff_tth_o')

hrm_y = EpicsMotor('XF:28IDC-OP:1{Mono:HRM-Ax:Y}Mtr', name='hrm_y')
hrm_b = EpicsMotor('XF:28IDC-OP:1{Mono:HRM-Ax:P}Mtr', name='hrm_b')
hrm_r = EpicsMotor('XF:28IDC-OP:1{Mono:HRM-Ax:R}Mtr', name='hrm_r')



shctl1 = EpicsMotor('XF:28IDC-ES:1{Sh2:Exp-Ax:5}Mtr', name='shctl1')
