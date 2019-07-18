/**********************************************************************/
/* (C) Crown copyright Met Office. All rights reserved.               */
/* For further details please refer to the file LICENCE.txt           */
/* which you should have received as part of this distribution.       */
/* *****************************COPYRIGHT******************************/
/*                                                                    */
/* This file is part of the SHUMlib packing library extension module  */
/* for Mule.                                                          */
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

#include <Python.h>
#include <numpy/arrayobject.h>
#include "c_shum_wgdos_packing.h"
#include "c_shum_byteswap.h"
#include "c_shum_wgdos_packing_version.h"

#if PY_MAJOR_VERSION >= 3
#define PyInt_FromLong PyLong_FromLong
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

MOD_INIT(um_packing);

static PyObject *wgdos_unpack_py(PyObject *self, PyObject *args);
static PyObject *wgdos_pack_py(PyObject *self, PyObject *args);
static PyObject *get_shumlib_version_py(PyObject *self, PyObject *args);

MOD_INIT(um_packing)
{
  PyDoc_STRVAR(um_packing__doc__,
  "This extension module provides access to the SHUMlib packing library.\n"
  );

  PyDoc_STRVAR(wgdos_unpack__doc__,
  "Unpack UM field data which has been packed using WGDOS packing.\n\n"
  "Usage:\n"
  "   um_packing.wgdos_unpack(bytes_in, mdi)\n\n"
  "Args:\n"
  "* bytes_in - Packed field byte-array.\n"
  "* mdi      - Missing data indicator.\n\n"
  "Returns:\n"
  "  2 Dimensional numpy.ndarray containing the unpacked field.\n" 
  );

  PyDoc_STRVAR(wgdos_pack__doc__,
  "Pack a UM field using WGDOS packing.\n\n"
  "Usage:\n"
  "  um_packing.wgdos_pack(field_in, mdi, accuracy)\n\n"
  "Args:\n"
  "* field_in - 2 Dimensional numpy.ndarray containing the field.\n"
  "* mdi      - Missing data indicator.\n"
  "* accuracy - Packing accuracy (power of 2).\n\n"
  "Returns:\n"
  "  Byte-array/stream (suitable to write straight to file).\n"
  );

  PyDoc_STRVAR(get_shumlib_version__doc__,
  "Returns the SHUMlib version number used the compile the library.\n\n"
  "Returns:\n"
  "* version - The version number as an integer in YYYYMMX format.\n"
  );

  static PyMethodDef um_packingMethods[] = {
    {"wgdos_unpack", wgdos_unpack_py, METH_VARARGS, wgdos_unpack__doc__},
    {"wgdos_pack", wgdos_pack_py, METH_VARARGS, wgdos_pack__doc__},
    {"get_shumlib_version", get_shumlib_version_py, 
                            METH_VARARGS, get_shumlib_version__doc__},
    {NULL, NULL, 0, NULL}
  };

  PyObject *mod;
  MOD_DEF(mod, "um_packing", um_packing__doc__, um_packingMethods);
  if (mod == NULL)
    return MOD_ERROR_VAL;

  import_array();
  return MOD_SUCCESS_VAL(mod);
}

static PyObject *wgdos_unpack_py(PyObject *self, PyObject *args)
{
  // Setup and obtain inputs passed from python
  char *bytes_in = NULL;
  int64_t n_bytes = 0;
  double mdi = 0.0;
  // Note the argument descriptors "s#d":
  //   - s#  a string followed by its size
  //   - d   an integer
  if (!PyArg_ParseTuple(args, "s#d", &bytes_in, &n_bytes, &mdi)) return NULL;

  // Cast self to void to avoid unused parameter errors
  (void) self;

  // Status variable to store various error codes
  int64_t status = 1;

  // Setup output array object and dimensions
  PyArrayObject *npy_array_out = NULL;
  npy_intp dims[2];

  // Error message string
  int64_t msg_len = 512;
  char err_msg[msg_len];

  // Perform a byte swap on the byte-array, if it looks like it is needed
  if (c_shum_get_machine_endianism() == littleEndian) {
    status = c_shum_byteswap(bytes_in,
                             n_bytes/(int64_t)sizeof(int32_t),
                             sizeof(int32_t),
                             &err_msg[0],
                             msg_len
                             );
    if (status != 0) {
      PyErr_SetString(PyExc_ValueError, &err_msg[0]);
      return NULL;
    }
  }

  // Now extract the word count, accuracy, number of rows and number of columns
  int64_t num_words;
  int64_t accuracy;
  int64_t cols;
  int64_t rows;

  status = c_shum_read_wgdos_header(bytes_in,
                                    &num_words,
                                    &accuracy,
                                    &cols,
                                    &rows,
                                    &err_msg[0],
                                    &msg_len
                                    );

  if (status != 0) {
    PyErr_SetString(PyExc_ValueError, &err_msg[0]);
    return NULL;
  }

  // Allocate space to hold the unpacked field
  double *dataout = (double*)calloc((size_t)(rows*cols), sizeof(double));
  if (dataout == NULL) {
    PyErr_SetString(PyExc_ValueError, "Unable to allocate memory for unpacking");
    return NULL;
  }

  // Call the WGDOS unpacking code
  int32_t *ptr_32 = (int32_t *)bytes_in;

  status = c_shum_wgdos_unpack(ptr_32,
                               &num_words,
                               &cols,
                               &rows,
                               &mdi,
                               dataout,
                               &err_msg[0],
                               &msg_len
                               );

  if (status != 0) {
    free(dataout);
    PyErr_SetString(PyExc_ValueError, &err_msg[0]);
    return NULL;
  }

  // Now form a numpy array object to return to python
  dims[0] = rows;
  dims[1] = cols;
  npy_array_out=(PyArrayObject *) PyArray_SimpleNewFromData(2, dims,
                                                            NPY_DOUBLE,
                                                            dataout);
  if (npy_array_out == NULL) {
    free(dataout);
    PyErr_SetString(PyExc_ValueError, "Failed to make numpy array");
    return NULL;
  }

  // Give python/numpy ownership of the memory storing the return array
  #if NPY_API_VERSION >= NPY_1_7_API_VERSION
  PyArray_ENABLEFLAGS(npy_array_out, NPY_ARRAY_OWNDATA);
  #else
  npy_array_out->flags = npy_array_out->flags | NPY_OWNDATA;
  #endif

  return (PyObject *)npy_array_out;
}

static PyObject *wgdos_pack_py(PyObject *self, PyObject *args)
{
  // Setup and obtain inputs passed from python
  PyArrayObject *datain;
  double mdi = 0.0;  
  int64_t accuracy = 0;
  // Note the argument descriptors "Odl":
  //   - O  a python object (here a numpy.ndarray)
  //   - d  an integer
  //   - l  a long integer
  if (!PyArg_ParseTuple(args, "Odl", 
                        &datain, 
                        &mdi, 
                        &accuracy)) return NULL;

  // Cast self to void to avoid unused paramter errors
  (void) self;

  npy_intp *dims = PyArray_DIMS(datain);
  int64_t rows = (int64_t) dims[0];
  int64_t cols = (int64_t) dims[1];
  double *field_ptr = (double *) PyArray_DATA(datain);

  // Allocate space for return value
  int64_t len_comp = rows*cols;
  int32_t *comp_field_ptr = 
    (int32_t*)calloc((size_t)(len_comp), sizeof(int32_t));

  int64_t status = 1;
  int64_t num_words;

  int64_t msg_len = 512;
  char err_msg[msg_len];

  status = c_shum_wgdos_pack(field_ptr,
                             &cols,
                             &rows,
                             &accuracy,
                             &mdi,
                             comp_field_ptr,
                             &len_comp,
                             &num_words,
                             &err_msg[0],
                             &msg_len
                             );

  if (status != 0) {
    free(comp_field_ptr);
    PyErr_SetString(PyExc_ValueError, &err_msg[0]);
    return NULL;
  }

  // Construct a char pointer array
  char *ptr_char = (char *)comp_field_ptr;
  Py_ssize_t out_len = (Py_ssize_t) (num_words * (int64_t)sizeof(int32_t));

  // Byteswap on the way out, if needed
  if (c_shum_get_machine_endianism() == littleEndian) {
    status = c_shum_byteswap(ptr_char, 
                             num_words,
                             sizeof(int32_t),
                             &err_msg[0],
                             msg_len
                             );
    if (status != 0) {
      PyErr_SetString(PyExc_ValueError, &err_msg[0]);
      return NULL;
    }
  }

  // Form a python string object to return to python
  PyObject *bytes_out = NULL;
  #if PY_MAJOR_VERSION >= 3
    bytes_out = PyBytes_FromStringAndSize(ptr_char, out_len);
  #else
    bytes_out = PyString_FromStringAndSize(ptr_char, out_len);
  #endif

  // Free the memory used by the integer array
  free(comp_field_ptr);

  return bytes_out;
}

static PyObject *get_shumlib_version_py(PyObject *self, PyObject *args)
{
  (void) self;
  (void) args;
  long version;
  version = (long) get_shum_wgdos_packing_version();

  PyObject *version_out = NULL;
  version_out = PyInt_FromLong(version);
  return version_out;
}
