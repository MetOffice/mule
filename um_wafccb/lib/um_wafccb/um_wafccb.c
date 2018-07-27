/**********************************************************************/
/* (C) Crown copyright Met Office. All rights reserved.               */
/* For further details please refer to the file LICENCE.txt           */
/* which you should have received as part of this distribution.       */
/* *****************************COPYRIGHT******************************/
/*                                                                    */
/* This file is part of the UM WAFCCB library extension module        */
/* for use with Mule.                                                 */
/*                                                                    */
/* Mule is free software: you can redistribute it and/or modify it    */
/* under the terms of the Modified BSD License, as published by the   */
/* Open Source Initiative.                                            */
/*                                                                    */
/* Mule is distributed in the hope that it will be useful,            */
/* but WITHOUT ANY WARRANTY; without even the implied warranty of     */
/* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the      */
/* Modified BSD License for more details.                             */
/*                                                                    */
/* You should have received a copy of the Modified BSD License        */
/* along with Mule.                                                   */
/* If not, see <http://opensource.org/licenses/BSD-3-Clause>.         */
/* ********************************************************************/

#ifndef NPY_1_7_API_VERSION
#define NPY_1_7_API_VERSION 0x00000007
#endif

#ifndef NPY_NO_DEPRECATED_API
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#endif

#include <stdbool.h>
#include <Python.h>
#include <numpy/arrayobject.h>

#include "wafccb.h"

#if PY_MAJOR_VERSION >= 3
#define MOD_ERROR_VAL NULL
#define MOD_SUCCESS_VAL(val) val
#define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
#define MOD_DEF(ob, name, doc, methods)               \
  static struct PyModuleDef moduledef = {             \
    PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
  ob = PyModule_Create(&moduledef);
#else
#define MOD_ERROR_VAL
#define MOD_SUCCESS_VAL(val)
#define MOD_INIT(name) PyMODINIT_FUNC init##name(void)
#define MOD_DEF(ob, name, doc, methods)               \
  ob = Py_InitModule3(name, methods, doc);
#endif

MOD_INIT(um_wafccb);

static PyObject *wafccb_py(PyObject *self, PyObject *args);

MOD_INIT(um_wafccb)
{
  PyDoc_STRVAR(um_wafccb__doc__,
  "Generate WAFC CB diagnostics.\n\n"
  "Usage:\n"
  "  um_wafccb.um_wafccb(cpnrt, blkcld, concld, ptheta, rmdi, icao_out)\n\n"
  "Args:\n"
  "* cpnrt    - Convective Precipitation Rate (2d array).\n"
  "* blkcld   - Bulk Cloud Fraction (3d array).\n"
  "* concld   - Convective Cloud Amount (3d array).\n"
  "* ptheta   - Theta Level Pressure (3d array).\n"
  "* rmdi     - Missing Data Indicator.\n"
  "* icao_out - Return ICAO heights instaed of pressures if True.\n\n"
  "Returns:\n"
  "A tuple containing 3 2d numpy.ndarrays, as follows:\n"
  "* p_cbb  - Cb Base Pressure / ICAO Height (if icao_out is True).\n"
  "* p_cbt  - Cb Top Pressure / ICAO Height (if icao_out is True).\n"
  "* cbhore - Cb Horizontal Extent.\n"
  );

  static PyMethodDef um_wafccbMethods[] = {
    {"wafccb", wafccb_py, METH_VARARGS, um_wafccb__doc__},
    {NULL, NULL, 0, NULL}
  };

  PyObject *mod;
  MOD_DEF(mod, "um_wafccb", um_wafccb__doc__, um_wafccbMethods);
  if (mod == NULL)
    return MOD_ERROR_VAL;

  import_array();
  return MOD_SUCCESS_VAL(mod);
}

static PyObject *wafccb_py(PyObject *self, PyObject *args)
{
  // Setup and obtain inputs passed from python
  double rmdi = 0.0;
  PyArrayObject *cpnrt;
  PyArrayObject *blkcld;
  PyArrayObject *concld;
  PyArrayObject *ptheta;
  PyObject *icao_out;

  // Note the argument descriptors "s#d":
  if (!PyArg_ParseTuple(args, "OOOOdO", 
                        &cpnrt, &blkcld, &concld, &ptheta, &rmdi, &icao_out
                        )) return NULL;

  // Cast self to void to avoid unused paramter errors
  (void) self;

  // Get dimensions of input fieldclim array
  npy_intp *dims_in = PyArray_DIMS(ptheta);
  int64_t cols   = (int64_t) dims_in[0];
  int64_t rows   = (int64_t) dims_in[1];
  int64_t levels = (int64_t) dims_in[2];

  double *cpnrt_ptr = (double *) PyArray_DATA(cpnrt);
  double *blkcld_ptr = (double *) PyArray_DATA(blkcld);
  double *concld_ptr = (double *) PyArray_DATA(concld);
  double *ptheta_ptr = (double *) PyArray_DATA(ptheta);

  // Get value of output flag
  bool icao_bool = (bool) PyObject_IsTrue(icao_out);

  // Allocate space for return value
  int64_t len_out = rows*cols;
  double *dataout_p_cbb = 
    (double*)calloc((size_t)(len_out), sizeof(double));
  if (dataout_p_cbb == NULL) {
    PyErr_SetString(PyExc_ValueError, "Unable to allocate memory for WAFC CB p_cbb");
    return NULL;
  } 
  double *dataout_p_cbt = 
    (double*)calloc((size_t)(len_out), sizeof(double));
  if (dataout_p_cbt == NULL) {
    PyErr_SetString(PyExc_ValueError, "Unable to allocate memory for WAFC CB p_cbt");
    return NULL;
  } 
  double *dataout_cbhore = 
    (double*)calloc((size_t)(len_out), sizeof(double));
  if (dataout_cbhore == NULL) {
    PyErr_SetString(PyExc_ValueError, "Unable to allocate memory for WAFC CB cbhore");
    return NULL;
  } 

  convact(&cols,
          &rows,
          &levels,
          cpnrt_ptr,
          blkcld_ptr,
          concld_ptr,
          ptheta_ptr,
          &rmdi,
          &icao_bool,
          dataout_p_cbb,
          dataout_p_cbt,
          dataout_cbhore);
          
  // Now form numpy array objects to return to python
  npy_intp dims_out[2];
  dims_out[0] = rows;
  dims_out[1] = cols;

  // Setup output array objects and dimensions
  PyArrayObject *npy_array_out_p_cbb = NULL;
  PyArrayObject *npy_array_out_p_cbt = NULL;
  PyArrayObject *npy_array_out_cbhore = NULL;

  npy_array_out_p_cbb=(PyArrayObject *) PyArray_SimpleNewFromData(2, dims_out,
                                                                  NPY_DOUBLE,
                                                                  dataout_p_cbb);
  if (npy_array_out_p_cbb == NULL) {
    free(dataout_p_cbb);
    PyErr_SetString(PyExc_ValueError, "Failed to make numpy array (p_cbb)");
    return NULL;
  }
  npy_array_out_p_cbt=(PyArrayObject *) PyArray_SimpleNewFromData(2, dims_out,
                                                                  NPY_DOUBLE,
                                                                  dataout_p_cbt);
  if (npy_array_out_p_cbt == NULL) {
    free(dataout_p_cbt);
    PyErr_SetString(PyExc_ValueError, "Failed to make numpy array (p_cbt)");
    return NULL;
  }
  npy_array_out_cbhore=(PyArrayObject *) PyArray_SimpleNewFromData(2, dims_out,
                                                                   NPY_DOUBLE,
                                                                   dataout_cbhore);
  if (npy_array_out_cbhore == NULL) {
    free(dataout_cbhore);
    PyErr_SetString(PyExc_ValueError, "Failed to make numpy array (cbhore)");
    return NULL;
  }

  // Give python/numpy ownership of the memory storing the return arrays
  #if NPY_API_VERSION >= NPY_1_7_API_VERSION
  PyArray_ENABLEFLAGS(npy_array_out_p_cbb, NPY_ARRAY_OWNDATA);
  PyArray_ENABLEFLAGS(npy_array_out_p_cbt, NPY_ARRAY_OWNDATA);
  PyArray_ENABLEFLAGS(npy_array_out_cbhore, NPY_ARRAY_OWNDATA);
  #else
  npy_array_out_p_cbb->flags = npy_array_out_p_cbb->flags | NPY_OWNDATA;
  npy_array_out_p_cbt->flags = npy_array_out_p_cbt->flags | NPY_OWNDATA;
  npy_array_out_cbhore->flags = npy_array_out_cbhore->flags | NPY_OWNDATA;
  #endif

  // Need to pack the items into a tuple to return them all
  PyObject *tuple_out = PyTuple_New(3);
  PyTuple_SetItem(tuple_out, 0, (PyObject *) npy_array_out_p_cbb);
  PyTuple_SetItem(tuple_out, 1, (PyObject *) npy_array_out_p_cbt);
  PyTuple_SetItem(tuple_out, 2, (PyObject *) npy_array_out_cbhore);

  return tuple_out;
}
