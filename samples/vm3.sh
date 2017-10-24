echo {{ password | default('proutos') }} | passwd --stdin root
